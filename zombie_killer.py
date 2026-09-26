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


def _process_born(api, pid):
    """The pid's current OS creation timestamp, or None if it cannot be
    verified alive right now (gone, access-denied, or a query failure)."""
    h = api.open(pid)
    if not h:
        return None
    try:
        if not api.alive(h):
            return None
        born, _ = api.times(h)
        return born
    except OSError:
        return None
    finally:
        api.close(h)


def broker_descendants(api, table, root_pid, root_born):
    """{pid: born} for `root_pid` and every descendant whose OS-reported
    creation time is at or after its alleged parent's.

    `table` is the raw (pid, ppid, name) list from Win32.process_table().
    The born-ordering check matters on Windows: a ppid can be silently
    reassigned once the real parent has exited (PID reuse), so a live
    process whose `born` predates the process it appears to descend from
    cannot actually be its child -- it is an unrelated process that merely
    inherited a stale ppid value. Same genealogical check snapshot()
    already applies via `parent_born <= born`.
    """
    children_of = {}
    for pid, ppid, _ in table:
        children_of.setdefault(ppid, []).append(pid)
    verified = {root_pid: root_born}
    stack = [(root_pid, root_born)]
    while stack:
        pid, born = stack.pop()
        for child_pid in children_of.get(pid, ()):
            if child_pid in verified:
                continue
            child_born = _process_born(api, child_pid)
            if child_born is None or child_born < born:
                continue
            verified[child_pid] = child_born
            stack.append((child_pid, child_born))
    return verified


def _tree_cpu_ticks(api, verified):
    """Sum of CPU ticks across `verified` ({pid: born}), read NOW.

    Re-checks each pid's CURRENT born against the recorded one before
    counting it -- a pid that was reused since `verified` was built is
    refused, not mis-summed. A pid that has exited (or any per-pid query
    failure) contributes 0, never an error -- a partially-exited tree must
    still be reported, not abort the whole walk. Must be called at the
    moment the caller wants to sample, not later -- CPU ticks are a live OS
    reading, not something recoverable in hindsight.
    """
    total = 0
    for pid, born in verified.items():
        h = api.open(pid)
        if not h:
            continue
        try:
            if not api.alive(h):
                continue
            cur_born, cpu = api.times(h)
            if cur_born != born:
                continue  # pid reused since verification -- not the same process
            total += cpu
        except OSError:
            continue
        finally:
            api.close(h)
    return total


def broker_snapshot(api, table):
    """One row per currently alive codex-broker root, sampled from `table`
    at THIS moment: {'pid', 'ppid', 'born', 'cwd', 'cpu', 'tree_size',
    'members'}. `members` is the born-verified {pid: born} descendant map
    from broker_descendants(); `cpu` is its summed CPU ticks, read live --
    call this right when `table` was captured, never after a delay (see
    _tree_cpu_ticks). `cwd` is the broker's OS working directory (the codex
    plugin runs one broker session per workspace cwd -- see
    detect_superseded_idle_brokers) or None if it could not be read.
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
        try:
            cwd = psutil.Process(pid).cwd()
        except (psutil.Error, OSError):
            cwd = None
        members = broker_descendants(api, table, pid, born)
        rows.append({'pid': pid, 'ppid': ppid, 'born': born, 'cwd': cwd,
                      'cpu': _tree_cpu_ticks(api, members),
                      'tree_size': len(members), 'members': members})
    rows.sort(key=lambda r: r['born'])
    return rows


def detect_superseded_idle_brokers(before_rows, after_rows, min_idle_seconds=600, now=None):
    """Read-only detection (TEIL A, T-20260924-303164669): a codex app-server
    broker that has been replaced by a NEWER broker FOR THE SAME workspace
    cwd, AND whose entire process tree showed zero CPU change between
    `before_rows` and `after_rows` (both from broker_snapshot(), taken some
    interval apart). NEVER terminates anything -- this is display/audit
    only; the only kill path stays safe_terminate()'s "parent dead" check.

    "Superseded" is scoped per cwd, not global: the codex plugin runs one
    broker session per workspace (`loadBrokerSession(cwd)`), so several
    brokers for DIFFERENT cwds are normal and simultaneously active. An
    older broker serving its own, still-open session can legitimately show
    0 CPU while blocked waiting on a model response -- comparing it against
    a newer broker for an unrelated cwd would misclassify active work as
    idle (the exact T-20260816-50 failure mode). A broker whose cwd could
    not be determined is never compared to anything and is therefore never
    a candidate -- unresolved identity must never be treated as "same
    session", only as "cannot confirm superseded".

    A cwd with only one broker (nothing newer for that same cwd) never
    produces a candidate, regardless of CPU or age -- "superseded" is a
    precondition, not a scoring factor.

    ponytail: idle-ness is one before/after sample (mirrors eligible()'s own
    single-interval CPU-delta check), not N minutes of continuous
    zero-CPU tracked across cycles. Upgrade path if that ever proves too
    eager: persist a per-root "first seen idle at" timestamp across cycle()
    calls (same pattern as `parent_cache`) and gate on that instead of/in
    addition to `min_idle_seconds` broker age.
    """
    now = time.time() if now is None else now
    before_by_pid = {r['pid']: r for r in before_rows}
    by_cwd: dict[str, list] = {}
    for row in after_rows:
        if row['cwd'] is None:
            continue  # unresolved identity -- never comparable, never a candidate
        by_cwd.setdefault(row['cwd'], []).append(row)
    findings = []
    for rows in by_cwd.values():
        if len(rows) < 2:
            continue
        rows = sorted(rows, key=lambda r: r['born'])
        *superseded, _current = rows  # highest `born` for this cwd stays untouched
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
                              'cwd': row['cwd'], 'tree_size': row['tree_size'],
                              'age_seconds': round(age)})
    return findings


def audit(path, event):
    with path.open('a', encoding='utf-8') as f:
        f.write(json.dumps({'at': time.time(), **event}, ensure_ascii=False) + '\n')


def cycle(api, apply=False, interval=2.0, min_age=1800, audit_path=None, parent_cache=None,
          broker_min_idle=600):
    deadline = time.monotonic() + 8
    # Cheap raw tables only, taken at the same two moments as the existing
    # snapshot() pair -- the (expensive, psutil-heavy) broker analysis is
    # deferred to the very end, see below.
    table_before = api.process_table()
    first, parents = snapshot(api,deadline)
    time.sleep(interval)
    table_after = api.process_table()
    second, current = snapshot(api,deadline)
    cache = parent_cache if parent_cache is not None else {}
    outcomes = []
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

    # Broker detection runs LAST and is fully isolated from everything above:
    # it must never delay or affect the parent-dead reap loop (budget: its
    # psutil.Process(pid).cmdline()/.cwd() calls happen only now, after the
    # loop already used what it needed of the 8s deadline), and a failure in
    # it (e.g. a descendant vanishing mid-walk) must never abort a cycle that
    # has, by this point, already completed its real work.
    try:
        broker_before = broker_snapshot(api, table_before)
        broker_after = broker_snapshot(api, table_after)
        for finding in detect_superseded_idle_brokers(broker_before, broker_after, broker_min_idle):
            if audit_path:
                audit(audit_path, {'event': 'broker-superseded-idle', **finding})
    except (OSError, psutil.Error) as exc:
        if audit_path:
            audit(audit_path, {'event': 'broker-detection-error', 'error': repr(exc)})

    return outcomes


def kill_broker_tree(api, root_pid, min_idle_seconds=600):
    """Opt-in MANUAL termination of one superseded, idle codex-broker tree
    (Tray-Menu action / explicit CLI call, per T-20260924-303164669 -- never
    invoked from the automatic scan/reap/watch cycle).

    Re-verifies the candidate FRESH (two brand-new samples) right before
    acting -- never trusts a detection result from an earlier cycle, in case
    the broker started doing work again in the meantime.
    """
    broker_before = broker_snapshot(api, api.process_table())
    time.sleep(2.0)
    broker_after = broker_snapshot(api, api.process_table())
    findings = detect_superseded_idle_brokers(broker_before, broker_after, min_idle_seconds)
    if not any(f['root_pid'] == root_pid for f in findings):
        return [], 'not-a-verified-candidate'
    row = next(r for r in broker_after if r['pid'] == root_pid)
    members = row['members']  # born-verified {pid: born}, see broker_descendants
    order = sorted(pid for pid in members if pid != root_pid) + [root_pid]  # children before the root
    killed = []
    for pid in order:
        expected_born = members[pid]
        h = api.open(pid, terminate=True)
        if not h:
            continue
        try:
            if not api.alive(h):
                continue
            cur_born, _ = api.times(h)
            if cur_born != expected_born:
                continue  # pid was reused between detection and this handle -- refuse
            if api.terminate(h):
                killed.append(pid)
        except OSError:
            continue
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
