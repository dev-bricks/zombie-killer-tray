"""Conservative Windows orphan reaper. Never kills an unverified process tree."""
from __future__ import annotations

import argparse
import ctypes
import json
import os
import threading
import time
import traceback
from ctypes import wintypes
from dataclasses import asdict, dataclass
from pathlib import Path

import psutil

LSP = frozenset({'rust-analyzer.exe', 'clangd.exe', 'gopls.exe', 'zls.exe'})
NODE_ENTRIES = frozenset({'typescript-language-server', 'pyright-langserver',
    'yaml-language-server', 'bash-language-server', 'vscode-json-languageserver'})
MCP_PACKAGES = frozenset({'ellmos-filecommander-mcp', 'ellmos-codecommander-mcp',
    'ellmos-controlcenter-mcp', 'ellmos-clatcher-mcp', 'ellmos-n8n-manager-mcp',
    'n8n-manager-mcp',
    '@modelcontextprotocol/server-filesystem', '@modelcontextprotocol/server-memory',
    '@modelcontextprotocol/server-sequential-thinking', '@upstash/context7-mcp'})
PYTHON_MODULES = frozenset({'pylsp', 'jedi_language_server', 'mcp_server_git',
    'mcp_server_fetch', 'mcp_server_time'})
ROOT = Path(__file__).resolve().parent


def classify(exe: str, argv: list[str]) -> str:
    """Only actual executable/module/first script argument counts, never free text."""
    name = Path(exe).name.lower()
    if name in LSP:
        return 'language-server'
    if name in {'python.exe', 'pythonw.exe', 'python3.exe'}:
        if len(argv) >= 3 and argv[1] == '-m' and argv[2] in PYTHON_MODULES:
            return 'language-server' if argv[2] in {'pylsp', 'jedi_language_server'} else 'mcp'
        return ''
    if name != 'node.exe' or len(argv) < 2 or argv[1].startswith('-'):
        return ''
    entry = argv[1].replace('\\', '/').lower()
    if not Path(argv[1]).is_absolute():
        return ''
    parts = entry.split('/')
    for i, part in enumerate(parts[:-1]):
        if part != 'node_modules':
            continue
        package = parts[i+1]
        start = i+2
        if package.startswith('@') and len(parts) > i+2:
            package += '/' + parts[i+2]
            start += 1
        suffix = '/'.join(parts[start:])
        # Do not classify an arbitrary file merely located below a known package.
        if package in MCP_PACKAGES and suffix in {
            'dist/index.js', 'build/index.js', 'dist/cli.js', 'build/cli.js', 'index.js'}:
            return 'mcp'
        if package in NODE_ENTRIES and suffix in {
            'lib/cli.mjs', 'lib/cli.js', 'out/cli.js', 'bin/pyright-langserver',
            'out/node/yamlServerMain.js'.lower(), 'out/node/jsonServerMain.js'.lower(),
            'server.js'}:
            return 'language-server'
    return ''


def is_codex_broker(exe: str, argv: list[str]) -> bool:
    """A `codex@openai-codex` plugin app-server-broker.mjs process.

    Deliberately kept OUT of classify()/Record.kind: that kind feeds the
    generic eligible()/safe_terminate() auto-kill path, whose only allowed
    kill criterion is "parent dead" (T-20260816-50 -- a watchdog once reaped
    an actively-used Codex-MCP cohort this way). A codex app-server-broker is
    designed to keep running independently of the CLI session that spawned
    it, so "parent dead" does NOT mean "safe to kill" for it -- an active
    broker could legitimately have a dead parent. Detection of a SUPERSEDED,
    idle broker therefore lives in its own read-only function
    (detect_superseded_idle_brokers) that never calls safe_terminate().
    """
    if Path(exe).name.lower() != 'node.exe' or len(argv) < 2 or argv[1].startswith('-'):
        return False
    entry = argv[1].replace('\\', '/').lower()
    if not Path(argv[1]).is_absolute():
        return False
    return entry.endswith('/scripts/app-server-broker.mjs') and '/openai-codex/' in entry


@dataclass(frozen=True)
class Record:
    pid: int
    ppid: int
    born: int
    cpu: int
    exe: str
    argv: tuple[str, ...]
    kind: str
    parent_dead: bool


def eligible(first: Record, second: Record, min_age: float, now: float) -> bool:
    return bool(first.kind and first.kind == second.kind
        and first.pid == second.pid and first.ppid == second.ppid
        and first.born == second.born and first.exe == second.exe
        and first.argv == second.argv and first.cpu == second.cpu
        and first.parent_dead and second.parent_dead
        and first.pid != os.getpid() and first.ppid > 0
        and now - (second.born / 10_000_000 - 11644473600) >= min_age)


class Win32:
    QUERY = 0x1000
    TERMINATE = 1
    SYNCHRONIZE = 0x100000

    def __init__(self):
        if os.name != 'nt':
            raise RuntimeError('Windows required')
        self.k = ctypes.WinDLL('kernel32', use_last_error=True)
        self.k.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        self.k.OpenProcess.restype = wintypes.HANDLE
        self.k.CloseHandle.argtypes = [wintypes.HANDLE]
        self.k.GetProcessTimes.argtypes = [wintypes.HANDLE] + [ctypes.POINTER(wintypes.FILETIME)] * 4
        self.k.GetProcessTimes.restype = wintypes.BOOL
        self.k.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        self.k.WaitForSingleObject.restype = wintypes.DWORD
        self.k.TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
        self.k.TerminateProcess.restype = wintypes.BOOL
        self.k.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD,
            wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
        self.k.QueryFullProcessImageNameW.restype = wintypes.BOOL

    def process_table(self):
        # One kernel snapshot supplies every PPID. psutil.ppid() on Windows
        # rebuilds the entire PPID map per call, making large fleets quadratic.
        class Entry(ctypes.Structure):
            _fields_ = [('dwSize',wintypes.DWORD),('cntUsage',wintypes.DWORD),
                ('pid',wintypes.DWORD),('heap',ctypes.c_size_t),('module',wintypes.DWORD),
                ('threads',wintypes.DWORD),('ppid',wintypes.DWORD),
                ('priority',wintypes.LONG),('flags',wintypes.DWORD),
                ('name',wintypes.WCHAR*260)]
        self.k.CreateToolhelp32Snapshot.argtypes=[wintypes.DWORD,wintypes.DWORD]
        self.k.CreateToolhelp32Snapshot.restype=wintypes.HANDLE
        for name in ('Process32FirstW','Process32NextW'):
            fn=getattr(self.k,name)
            fn.argtypes=[wintypes.HANDLE,ctypes.POINTER(Entry)]
            fn.restype=wintypes.BOOL
        h=self.k.CreateToolhelp32Snapshot(2,0)
        if h == ctypes.c_void_p(-1).value:
            raise OSError('process snapshot failed')
        try:
            row = Entry()
            row.dwSize = ctypes.sizeof(row)
            rows = []
            valid = self.k.Process32FirstW(h, ctypes.byref(row))
            while valid:
                rows.append((row.pid, row.ppid, row.name))
                valid = self.k.Process32NextW(h, ctypes.byref(row))
            if ctypes.get_last_error() != 18:
                raise OSError('incomplete process snapshot')
            return rows
        finally:
            self.close(h)

    def image(self, h):
        text = ctypes.create_unicode_buffer(32768)
        length = wintypes.DWORD(len(text))
        if not self.k.QueryFullProcessImageNameW(h, 0, text, ctypes.byref(length)):
            raise OSError('process image unavailable')
        return text.value

    def open(self, pid, terminate=False):
        return self.k.OpenProcess(self.QUERY | self.SYNCHRONIZE |
            (self.TERMINATE if terminate else 0), False, pid)

    def close(self, h):
        self.k.CloseHandle(h)

    def times(self, h):
        created, exited, kernel, user = (wintypes.FILETIME() for _ in range(4))
        if not self.k.GetProcessTimes(h, ctypes.byref(created), ctypes.byref(exited),
                                      ctypes.byref(kernel), ctypes.byref(user)):
            raise OSError('GetProcessTimes failed')

        def ticks(ft):
            return (ft.dwHighDateTime << 32) | ft.dwLowDateTime

        return ticks(created), ticks(kernel) + ticks(user)

    def alive(self, h):
        return self.k.WaitForSingleObject(h, 0) == 258

    def parent_dead(self, pid):
        if pid <= 0:
            return False
        h = self.open(pid)
        if not h:
            # ERROR_INVALID_PARAMETER: PID does not exist. Access denied is UNKNOWN.
            return ctypes.get_last_error() == 87
        try:
            return self.k.WaitForSingleObject(h, 0) == 0
        finally:
            self.close(h)

    def terminate(self, h):
        if not self.k.TerminateProcess(h, 1):
            return False
        return self.k.WaitForSingleObject(h, 2000) == 0


def snapshot(api, deadline=None):
    records = {}
    identities = {}
    table_started = time.time()
    allowed_names = LSP | {'node.exe','python.exe','pythonw.exe','python3.exe'}
    for pid,ppid,name in api.process_table():
        if deadline is not None and time.monotonic() > deadline:
            raise TimeoutError('read-only process snapshot deadline exceeded')
        if name.lower() not in allowed_names:
            continue
        try:
            h = api.open(pid)
            if not h:
                continue
            try:
                born, cpu = api.times(h)
                exe=api.image(h)
                # The retained handle pins the PID incarnation during cmdline read.
                argv=psutil.Process(pid).cmdline()
                kind=classify(exe,argv)
                if not kind:
                    continue
                if not api.alive(h):
                    continue
                # The table might predate PID reuse: creation must predate table read.
                if born / 10_000_000 - 11644473600 > table_started:
                    continue
                records[pid] = Record(pid, ppid, born, cpu, exe,
                    tuple(argv), kind, api.parent_dead(ppid))
                if ppid > 0 and str(ppid) not in identities:
                    ph=api.open(ppid)
                    if ph:
                        try:
                            parent_born,_=api.times(ph)
                            if api.alive(ph) and parent_born <= born:
                                identities[str(ppid)]={'pid':ppid,'born':parent_born,
                                    'exe':api.image(ph),'seen_at':time.time()}
                        finally:
                            api.close(ph)
            finally:
                api.close(h)
        except (psutil.Error, OSError, ValueError):
            continue
    return records, identities


def safe_terminate(api, first, second, min_age=1800, now=None):
    """Retain the verified handle until termination; never readdress a PID to kill."""
    if not eligible(first, second, min_age, time.time() if now is None else now):
        return False, 'sample-gate'
    h = api.open(second.pid, terminate=True)
    if not h:
        return False, 'open-denied-or-gone'
    try:
        born, cpu = api.times(h)
        if born != second.born or cpu != second.cpu or not api.alive(h):
            return False, 'incarnation-or-cpu-changed'
        if not api.parent_dead(second.ppid):
            return False, 'parent-live-or-unknown'
        # Parent PID reuse is deliberately protected as "live", not guessed away.
        born, cpu = api.times(h)
        if born != second.born or cpu != second.cpu:
            return False, 'cpu-changed-before-terminate'
        return api.terminate(h), 'verified-handle-terminate'
    except OSError:
        return False, 'query-failed'
    finally:
        api.close(h)


def broker_descendants(table, root_pid):
    """All pids in the process tree rooted at `root_pid` (root included).

    `table` is the raw (pid, ppid, name) list from Win32.process_table().
    """
    children = {}
    for pid, ppid, _ in table:
        children.setdefault(ppid, []).append(pid)
    seen = {root_pid}
    stack = [root_pid]
    while stack:
        pid = stack.pop()
        for child in children.get(pid, ()):
            if child not in seen:
                seen.add(child)
                stack.append(child)
    return seen


def _tree_cpu_ticks(api, pids):
    """Sum of CPU ticks across every currently-alive pid in `pids`, read NOW.

    A pid that has already exited contributes 0, never an error -- a
    partially-exited tree must still be reported, not skipped. Must be
    called at the moment the caller wants to sample, not later -- CPU ticks
    are a live OS reading, not something recoverable in hindsight.
    """
    total = 0
    for pid in pids:
        h = api.open(pid)
        if not h:
            continue
        try:
            if api.alive(h):
                _, cpu = api.times(h)
                total += cpu
        finally:
            api.close(h)
    return total


def broker_snapshot(api, table):
    """One row per currently alive codex-broker root, sampled from `table`
    at THIS moment: {'pid', 'ppid', 'born', 'cpu', 'tree_size'}. `cpu` is the
    summed CPU ticks of the broker's entire descendant tree, read live --
    call this right when `table` was captured, never after a delay (see
    _tree_cpu_ticks).
    """
    rows = []
    for pid, ppid, name in table:
        if name.lower() != 'node.exe':
            continue
        h = api.open(pid)
        if not h:
            continue
        try:
            if not api.alive(h):
                continue
            born, _ = api.times(h)
            exe = api.image(h)
            argv = psutil.Process(pid).cmdline()
        except (psutil.Error, OSError, ValueError):
            continue
        finally:
            api.close(h)
        if not is_codex_broker(exe, argv):
            continue
        pids = broker_descendants(table, pid)
        rows.append({'pid': pid, 'ppid': ppid, 'born': born,
                      'cpu': _tree_cpu_ticks(api, pids), 'tree_size': len(pids)})
    rows.sort(key=lambda r: r['born'])
    return rows


def detect_superseded_idle_brokers(before_rows, after_rows, min_idle_seconds=600, now=None):
    """Read-only detection (TEIL A, T-20260924-303164669): a codex app-server
    broker that has been replaced by a newer broker AND whose entire process
    tree showed zero CPU change between `before_rows` and `after_rows` (both
    from broker_snapshot(), taken some interval apart). NEVER terminates
    anything -- this is display/audit only; the only kill path stays
    safe_terminate()'s "parent dead" check.

    A lone broker (nothing newer has replaced it) is never a candidate,
    regardless of its CPU or age -- "superseded" is a precondition, not a
    scoring factor.

    ponytail: idle-ness is one before/after sample (mirrors eligible()'s own
    single-interval CPU-delta check), not N minutes of continuous
    zero-CPU tracked across cycles. Upgrade path if that ever proves too
    eager: persist a per-root "first seen idle at" timestamp across cycle()
    calls (same pattern as `parent_cache`) and gate on that instead of/in
    addition to `min_idle_seconds` broker age.
    """
    now = time.time() if now is None else now
    if len(after_rows) < 2:
        return []
    *superseded, _current = after_rows  # highest `born` = current, untouched
    before_by_pid = {r['pid']: r for r in before_rows}
    findings = []
    for row in superseded:
        age = now - (row['born'] / 10_000_000 - 11644473600)
        if age < min_idle_seconds:
            continue
        before = before_by_pid.get(row['pid'])
        # Different `born` would mean PID reuse -- not the same incarnation.
        if before is None or before['born'] != row['born']:
            continue
        if before['cpu'] != row['cpu']:
            continue  # still doing work -- not idle, not a candidate
        findings.append({'root_pid': row['pid'], 'root_ppid': row['ppid'],
                          'tree_size': row['tree_size'], 'age_seconds': round(age)})
    return findings


def audit(path, event):
    with path.open('a', encoding='utf-8') as f:
        f.write(json.dumps({'at': time.time(), **event}, ensure_ascii=False) + '\n')


def cycle(api, apply=False, interval=2.0, min_age=1800, audit_path=None, parent_cache=None,
          broker_min_idle=600):
    deadline = time.monotonic() + 8
    broker_before = broker_snapshot(api, api.process_table())
    first, parents = snapshot(api,deadline)
    time.sleep(interval)
    broker_after = broker_snapshot(api, api.process_table())
    second, current = snapshot(api,deadline)
    cache = parent_cache if parent_cache is not None else {}
    outcomes = []
    # Read-only, independent of the kill loop below: display/log only, never
    # terminate (see detect_superseded_idle_brokers docstring).
    for finding in detect_superseded_idle_brokers(broker_before, broker_after, broker_min_idle):
        if audit_path:
            audit(audit_path, {'event': 'broker-superseded-idle', **finding})
    for pid, b in second.items():
        if time.monotonic() > deadline:
            if audit_path:
                audit(audit_path, {'event': 'cycle-deadline', 'apply': False})
            break
        a = first.get(pid)
        if a is None or not eligible(a, b, min_age, time.time()):
            continue
        # Only identify a parent actually observed for this same child's incarnation.
        old = cache.get((b.pid, b.born, b.ppid))
        parent = parents.get(str(b.ppid)) or old
        if apply and audit_path:
            # A failed audit write prevents the mutation, not just its report.
            audit(audit_path, {'event': 'terminate-intent', 'child': asdict(b),
                              'parent_last_observed': parent})
        killed, reason = safe_terminate(api, a, b, min_age) if apply else (False, 'preview')
        event = {'child': asdict(b), 'parent_last_observed': parent,
                 'killed': killed, 'reason': reason}
        outcomes.append(event)
        if audit_path:
            audit(audit_path, event)
    next_cache = {}
    for b in second.values():
        key = (b.pid, b.born, b.ppid)
        parent = current.get(str(b.ppid)) or cache.get(key)
        if parent and parent['born'] <= b.born:
            next_cache[key] = parent
    cache.clear()
    cache.update(next_cache)
    return outcomes


def kill_broker_tree(api, root_pid, min_idle_seconds=600):
    """Opt-in MANUAL termination of one superseded, idle codex-broker tree
    (Tray-Menu action / explicit CLI call, per T-20260924-303164669 -- never
    invoked from the automatic scan/reap/watch cycle).

    Re-verifies the candidate FRESH (two brand-new samples) right before
    acting -- never trusts a detection result from an earlier cycle, in case
    the broker started doing work again in the meantime.
    """
    table_before = api.process_table()
    broker_before = broker_snapshot(api, table_before)
    time.sleep(2.0)
    table_after = api.process_table()
    broker_after = broker_snapshot(api, table_after)
    findings = detect_superseded_idle_brokers(broker_before, broker_after, min_idle_seconds)
    if not any(f['root_pid'] == root_pid for f in findings):
        return [], 'not-a-verified-candidate'
    pids = broker_descendants(table_after, root_pid)
    order = sorted(pids - {root_pid}) + [root_pid]  # children before the root
    killed = []
    for pid in order:
        h = api.open(pid, terminate=True)
        if not h:
            continue
        try:
            if api.alive(h) and api.terminate(h):
                killed.append(pid)
        finally:
            api.close(h)
    return killed, 'killed'


def log_worker_error(text):
    try:
        with (ROOT / 'zombie_worker_errors.log').open('a', encoding='utf-8') as f:
            f.write(f'{time.strftime("%Y-%m-%dT%H:%M:%S")} {text}\n')
    except OSError:
        pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['scan', 'reap', 'watch', 'broker-report', 'kill-broker'])
    parser.add_argument('--yes', action='store_true')
    parser.add_argument('--interval', type=float, default=10)
    parser.add_argument('--min-age', type=float, default=1800)
    parser.add_argument('--broker-min-idle', type=float, default=600)
    parser.add_argument('--broker-pid', type=int,
        help='root pid for kill-broker (opt-in manual termination, requires --yes)')
    parser.add_argument('--parent-pid', type=int)
    args = parser.parse_args()
    if args.action in ('scan', 'reap', 'watch') and (args.min_age < 30 or args.interval < 3):
        parser.error('min-age >=30 and interval >=3 required')
    api = Win32()

    if args.action == 'broker-report':
        # Standardmaessig nur anzeigen: read-only, keine Terminierung.
        broker_before = broker_snapshot(api, api.process_table())
        time.sleep(2.0)
        broker_after = broker_snapshot(api, api.process_table())
        findings = detect_superseded_idle_brokers(broker_before, broker_after, args.broker_min_idle)
        print(json.dumps({'findings': findings}), flush=True)
        return

    if args.action == 'kill-broker':
        if not args.broker_pid or not args.yes:
            parser.error('kill-broker requires --broker-pid and --yes (opt-in only)')
        killed, reason = kill_broker_tree(api, args.broker_pid, args.broker_min_idle)
        audit(ROOT / 'zombie_events.jsonl', {'event': 'broker-manual-kill',
            'root_pid': args.broker_pid, 'killed_pids': killed, 'reason': reason})
        print(json.dumps({'killed_pids': killed, 'reason': reason}), flush=True)
        return

    if args.parent_pid:
        # Pin the tray incarnation once. A reused PID cannot keep this worker alive.
        parent_handle = api.open(args.parent_pid)
        if not parent_handle or not api.alive(parent_handle):
            raise RuntimeError('tray parent cannot be verified')
        def watch_parent():
            while api.alive(parent_handle):
                time.sleep(0.5)
            api.close(parent_handle)
            os._exit(0)
        threading.Thread(target=watch_parent, daemon=True).start()
    cache = {}
    while True:
        started = time.monotonic()
        try:
            outcomes = cycle(api, apply=args.action != 'scan' and args.yes,
                min_age=args.min_age, parent_cache=cache,
                audit_path=ROOT / 'zombie_events.jsonl')
            event = {'cycle_at': time.time(), 'apply': args.yes, 'count': len(outcomes)}
            audit(ROOT / 'zombie_events.jsonl', event)
        except Exception:
            # The worker runs windowless without stderr; an uncaught error used to
            # end it with rc=1 and take the tray down. Log it and keep watching.
            log_worker_error(traceback.format_exc())
            if args.action != 'watch':
                raise
            cache.clear()
            time.sleep(args.interval)
            continue
        if args.action != 'watch':
            print(json.dumps({'cycle': event, 'outcomes': outcomes}), flush=True)
        if args.action != 'watch':
            return
        time.sleep(max(0, args.interval - (time.monotonic() - started)))


if __name__ == '__main__':
    try:
        main()
    except Exception:
        log_worker_error(traceback.format_exc())
        raise
