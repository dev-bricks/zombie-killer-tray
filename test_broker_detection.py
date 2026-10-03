"""Tests for the codex-broker detection added for T-20260924-303164669.

Covers: is_codex_broker() classification, broker_descendants() genealogy
walk, broker_snapshot()/detect_superseded_idle_brokers()/
track_broker_idle_streaks() (read-only detect/report only -- see below),
and -- critically -- that none of this feeds the existing automatic
eligible()/safe_terminate() kill path (Auflage T-20260816-50: kill criterion
stays exclusively "parent dead").

Also covers the review findings on PR #3 (head fc6a5a6, then 04735c9):
1. (fixed in 04735c9, superseded by the point below) a kill_broker_tree()
   pid-reuse refusal -- the function itself was later REMOVED, see 5.
2. broker_descendants must ignore a child whose born predates its alleged
   parent (stale/reassigned ppid).
3. "superseded" must be scoped per cwd, not global (the plugin runs one
   broker per workspace; several concurrently active brokers are normal).
4. A per-pid times() failure inside broker detection must never abort
   cycle() (and therefore never affect the parent-dead reap loop).
5. Two further findings on 04735c9 -- (A) cycle()'s broker before/after
   pair used to be sampled back-to-back with ~0 real time between them
   (CPU delta always ~0, so almost every broker looked idle); it is now
   taken across the SAME real `interval` gap the reap loop already sleeps
   for (see table_before/table_after in cycle()). (B) a broker that failed
   its 150ms endpoint-ready check is superseded but NEVER killed by the
   codex plugin itself (ensureBrokerSession's teardown only removes its
   session files, not the process -- see broker-lifecycle.mjs), so it can
   still be doing real work (blocked on a model response = ~0 CPU) when a
   single before/after sample catches it. Reliably telling that apart from
   "actually abandoned" would need the plugin's OWN broker.json/jobs
   bookkeeping, which requires reproducing its workspace-root git
   resolution and internal hashing from outside the plugin -- not reliably
   resolvable here. Per the decided fallback for that case, kill_broker_tree()
   and the `kill-broker` CLI action were REMOVED (detect/report only from
   here on); what remains is track_broker_idle_streaks(), which requires
   the SAME idle reading to hold across several separately-sampled cycle()
   calls (a real, cumulative multi-minute span) before a finding is marked
   `confirmed` -- raising confidence without ever acting on it.
"""
import sys
import time
import unittest
from pathlib import Path
from unittest.mock import patch

_SRC = str(Path(__file__).resolve().parent / "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

import zombie_killer_tray.killer as z

FILETIME_EPOCH = 11644473600


def ft(now_offset_seconds):
    return int((time.time() + now_offset_seconds + FILETIME_EPOCH) * 1e7)


class FakeMultiAPI:
    """Minimal multi-process fake keyed by pid; pid doubles as the handle."""

    def __init__(self, procs):
        # procs: {pid: {'ppid', 'name', 'born', 'cpu', 'exe', 'alive'}}
        self.procs = procs
        self.terminated = []
        self.raise_times_for = set()

    def process_table(self):
        return [(pid, p['ppid'], p['name']) for pid, p in self.procs.items()]

    def open(self, pid, terminate=False):
        return pid if pid in self.procs else None

    def close(self, handle):
        pass

    def alive(self, handle):
        return bool(self.procs.get(handle, {}).get('alive'))

    def times(self, handle):
        if handle in self.raise_times_for:
            raise OSError('GetProcessTimes failed')
        p = self.procs[handle]
        return p['born'], p['cpu']

    def image(self, handle):
        return self.procs[handle]['exe']

    def terminate(self, handle):
        self.terminated.append(handle)
        self.procs[handle]['alive'] = False
        return True

    def parent_dead(self, pid):
        return False


class FakeCmdline:
    """Stand-in for psutil.Process(pid): .cmdline() and .cwd()."""

    def __init__(self, argv_by_pid, cwd_by_pid=None):
        self.argv_by_pid = argv_by_pid
        self.cwd_by_pid = cwd_by_pid or {}

    def __call__(self, pid):
        inst = unittest.mock.Mock()
        inst.cmdline.return_value = self.argv_by_pid[pid]
        inst.cwd.return_value = self.cwd_by_pid.get(pid, 'C:/ws')
        return inst


BROKER_EXE = 'C:/node.exe'
BROKER_ARGV = ['node.exe',
    'C:/Users/User/.claude/plugins/cache/openai-codex/codex/1.0.6/scripts/app-server-broker.mjs']


def _snap(api, argv_map, cwd_map=None):
    """broker_snapshot() taken THIS instant, matching production timing
    (cpu is summed live, immediately -- see broker_snapshot docstring)."""
    with patch.object(z.psutil, 'Process', FakeCmdline(argv_map, cwd_map)):
        return z.broker_snapshot(api, api.process_table())


class IsCodexBrokerTests(unittest.TestCase):
    def test_recognizes_broker_script(self):
        self.assertTrue(z.is_codex_broker(BROKER_EXE, BROKER_ARGV))

    def test_rejects_other_node_scripts(self):
        self.assertFalse(z.is_codex_broker('C:/node.exe',
            ['node.exe', 'C:/node_modules/ellmos-filecommander-mcp/dist/index.js']))

    def test_rejects_relative_path(self):
        self.assertFalse(z.is_codex_broker(BROKER_EXE,
            ['node.exe', 'scripts/app-server-broker.mjs']))

    def test_classify_never_returns_a_kind_for_the_broker_script(self):
        # Safety property the docstrings rely on: the generic auto-kill
        # pipeline (classify() -> Record.kind -> eligible()/safe_terminate())
        # must never see this process at all.
        self.assertEqual(z.classify(BROKER_EXE, BROKER_ARGV), '')


class BrokerDescendantsTests(unittest.TestCase):
    def test_walks_multi_level_tree_and_ignores_unrelated_pids(self):
        procs = {
            1: {'ppid': 0, 'name': 'node.exe', 'born': ft(-100), 'cpu': 0, 'exe': '', 'alive': True},
            2: {'ppid': 1, 'name': 'child.exe', 'born': ft(-99), 'cpu': 0, 'exe': '', 'alive': True},
            3: {'ppid': 2, 'name': 'grandchild.exe', 'born': ft(-98), 'cpu': 0, 'exe': '', 'alive': True},
            99: {'ppid': 0, 'name': 'unrelated.exe', 'born': ft(-50), 'cpu': 0, 'exe': '', 'alive': True},
        }
        api = FakeMultiAPI(procs)
        table = api.process_table()
        members = z.broker_descendants(api, table, 1, procs[1]['born'])
        self.assertEqual(set(members), {1, 2, 3})

    def test_ignores_a_child_born_before_its_alleged_parent(self):
        """Regression (review finding 2): a live pid whose ppid points at our
        root but whose OWN born predates the root's cannot really be its
        child -- e.g. an unrelated process that inherited a stale, reused
        ppid after the real parent died. It must be excluded from the tree
        and the reported CPU sum."""
        root_born = ft(-100)
        procs = {
            1: {'ppid': 0, 'name': 'node.exe', 'born': root_born, 'cpu': 0, 'exe': '', 'alive': True},
            # ppid=1 but born BEFORE the root -- not a real descendant.
            50: {'ppid': 1, 'name': 'unrelated.exe', 'born': ft(-9999), 'cpu': 777, 'exe': '', 'alive': True},
        }
        api = FakeMultiAPI(procs)
        table = api.process_table()
        members = z.broker_descendants(api, table, 1, root_born)
        self.assertEqual(set(members), {1})
        self.assertEqual(z._tree_cpu_ticks(api, members), 0)


class DetectSupersededIdleBrokersTests(unittest.TestCase):
    def _procs(self, old_born_offset, old_cpu, new_born_offset=-5, new_cpu=1):
        return {
            10: {'ppid': 1, 'name': 'node.exe', 'born': ft(old_born_offset),
                 'cpu': old_cpu, 'exe': BROKER_EXE, 'alive': True},
            11: {'ppid': 10, 'name': 'python.exe', 'born': ft(old_born_offset + 1),
                 'cpu': 5, 'exe': 'C:/python.exe', 'alive': True},
            20: {'ppid': 1, 'name': 'node.exe', 'born': ft(new_born_offset),
                 'cpu': new_cpu, 'exe': BROKER_EXE, 'alive': True},
        }

    def test_lone_broker_is_never_a_candidate(self):
        procs = {20: self._procs(-1000, 0)[20]}
        api = FakeMultiAPI(procs)
        rows = _snap(api, {20: BROKER_ARGV})
        findings = z.detect_superseded_idle_brokers(rows, rows)
        self.assertEqual(findings, [])

    def test_superseded_idle_old_broker_is_flagged(self):
        procs = self._procs(old_born_offset=-3600, old_cpu=42)
        api = FakeMultiAPI(procs)
        argv_map = {10: BROKER_ARGV, 20: BROKER_ARGV}  # same default cwd 'C:/ws' for both
        rows = _snap(api, argv_map)  # nothing changed -> same rows twice is fine
        findings = z.detect_superseded_idle_brokers(rows, rows, min_idle_seconds=600)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]['root_pid'], 10)
        self.assertEqual(findings[0]['tree_size'], 2)  # broker + its python child
        self.assertGreaterEqual(findings[0]['age_seconds'], 3599)

    def test_still_current_broker_is_never_flagged(self):
        procs = self._procs(old_born_offset=-3600, old_cpu=42)
        api = FakeMultiAPI(procs)
        argv_map = {10: BROKER_ARGV, 20: BROKER_ARGV}
        rows = _snap(api, argv_map)
        findings = z.detect_superseded_idle_brokers(rows, rows, min_idle_seconds=600)
        self.assertNotIn(20, [f['root_pid'] for f in findings])

    def test_active_old_broker_is_not_flagged(self):
        procs = self._procs(old_born_offset=-3600, old_cpu=42)
        api = FakeMultiAPI(procs)
        argv_map = {10: BROKER_ARGV, 20: BROKER_ARGV}
        before = _snap(api, argv_map)
        procs[11]['cpu'] += 3  # child did work between the two samples
        after = _snap(api, argv_map)
        findings = z.detect_superseded_idle_brokers(before, after, min_idle_seconds=600)
        self.assertEqual(findings, [])

    def test_too_young_superseded_broker_is_not_flagged(self):
        procs = self._procs(old_born_offset=-30, old_cpu=42)  # only 30s old
        api = FakeMultiAPI(procs)
        argv_map = {10: BROKER_ARGV, 20: BROKER_ARGV}
        rows = _snap(api, argv_map)
        findings = z.detect_superseded_idle_brokers(rows, rows, min_idle_seconds=600)
        self.assertEqual(findings, [])

    def test_exited_between_samples_is_not_flagged(self):
        procs = self._procs(old_born_offset=-3600, old_cpu=42)
        api = FakeMultiAPI(procs)
        before = _snap(api, {10: BROKER_ARGV, 20: BROKER_ARGV})
        del api.procs[10]  # gone in the second sample
        after = _snap(api, {20: BROKER_ARGV})
        findings = z.detect_superseded_idle_brokers(before, after, min_idle_seconds=600)
        self.assertEqual(findings, [])

    def test_older_broker_for_a_different_cwd_is_never_flagged(self):
        """Regression (review finding 3): the plugin runs one broker session
        per workspace cwd (loadBrokerSession(cwd)) -- several concurrently
        active brokers for DIFFERENT cwds are normal, not "superseded". An
        older broker legitimately blocked waiting on a model response for
        its OWN session shows 0 CPU too; it must not be flagged just because
        an unrelated, newer broker for another workspace exists."""
        procs = self._procs(old_born_offset=-3600, old_cpu=42)
        api = FakeMultiAPI(procs)
        argv_map = {10: BROKER_ARGV, 20: BROKER_ARGV}
        cwd_map = {10: 'C:/workspace-a', 20: 'C:/workspace-b'}
        rows = _snap(api, argv_map, cwd_map)
        findings = z.detect_superseded_idle_brokers(rows, rows, min_idle_seconds=600)
        self.assertEqual(findings, [])

    def test_superseded_within_the_same_cwd_is_still_flagged(self):
        """Companion to the above: two brokers for the SAME cwd (a real
        hand-off) must still be detected -- the cwd scoping must not
        silently disable detection altogether."""
        procs = self._procs(old_born_offset=-3600, old_cpu=42)
        api = FakeMultiAPI(procs)
        argv_map = {10: BROKER_ARGV, 20: BROKER_ARGV}
        cwd_map = {10: 'C:/workspace-a', 20: 'C:/workspace-a'}
        rows = _snap(api, argv_map, cwd_map)
        findings = z.detect_superseded_idle_brokers(rows, rows, min_idle_seconds=600)
        self.assertEqual([f['root_pid'] for f in findings], [10])

    def test_unresolvable_cwd_is_never_a_candidate(self):
        """A broker whose cwd could not be read must never be compared to
        anything -- unresolved identity must never be treated as "confirmed
        same session"."""
        import psutil as real_psutil

        procs = self._procs(old_born_offset=-3600, old_cpu=42)
        api = FakeMultiAPI(procs)

        class RaisingCwd(FakeCmdline):
            def __call__(self, pid):
                inst = super().__call__(pid)
                inst.cwd.side_effect = real_psutil.Error('no such process')
                return inst

        with patch.object(z.psutil, 'Process', RaisingCwd({10: BROKER_ARGV, 20: BROKER_ARGV})):
            rows = z.broker_snapshot(api, api.process_table())
        self.assertTrue(all(r['cwd'] is None for r in rows))
        findings = z.detect_superseded_idle_brokers(rows, rows, min_idle_seconds=600)
        self.assertEqual(findings, [])


class BrokerDetectionIsolationTests(unittest.TestCase):
    """Regression (review finding 4): a per-pid times() failure inside
    broker detection must never abort cycle(), and therefore never affect
    the parent-dead reap loop that runs before it."""

    def test_times_failure_on_a_descendant_does_not_raise(self):
        procs = {
            10: {'ppid': 1, 'name': 'node.exe', 'born': ft(-3600), 'cpu': 42,
                 'exe': BROKER_EXE, 'alive': True},
            11: {'ppid': 10, 'name': 'python.exe', 'born': ft(-3599), 'cpu': 5,
                 'exe': 'C:/python.exe', 'alive': True},
            20: {'ppid': 1, 'name': 'node.exe', 'born': ft(-5), 'cpu': 1,
                 'exe': BROKER_EXE, 'alive': True},
        }
        api = FakeMultiAPI(procs)
        api.raise_times_for = {11}
        with patch.object(z.psutil, 'Process', FakeCmdline({10: BROKER_ARGV, 20: BROKER_ARGV})):
            rows = z.broker_snapshot(api, api.process_table())  # must not raise
        broker_10 = next(r for r in rows if r['pid'] == 10)
        # The failing child could not be verified alive at all (_process_born
        # swallows the OSError), so it is excluded from the tree entirely --
        # only the root's own, successfully-read CPU is counted. The point
        # is that the whole walk/snapshot did not abort, not the exact sum.
        self.assertEqual(broker_10['cpu'], 42)
        self.assertEqual(broker_10['tree_size'], 1)

    def test_cycle_survives_and_still_reaps_when_broker_detection_errors(self):
        r = z.Record(987654, 987653, int((time.time() - 3600 + 11644473600) * 1e7),
                     23, 'C:/bin/clangd.exe', ('clangd.exe',), 'language-server', True)

        class ReapOnlyAPI(FakeMultiAPI):
            def open(self, pid, terminate=False):
                return 'pinned-handle'

            def alive(self, handle):
                return True

            def times(self, handle):
                return r.born, r.cpu

            def terminate(self, handle):
                self.terminated.append(handle)
                return True

            def parent_dead(self, pid):
                return True

        api = ReapOnlyAPI({})
        with patch.object(z, 'snapshot', return_value=({r.pid: r}, {})), \
             patch.object(z, 'broker_snapshot', side_effect=OSError('boom')), \
             patch.object(z.time, 'sleep'):
            outcomes = z.cycle(api, apply=True)  # must not raise
        self.assertTrue(outcomes and outcomes[0]['killed'])  # the reap loop still ran


class TrackBrokerIdleStreaksTests(unittest.TestCase):
    """kill_broker_tree() and the `kill-broker` CLI action were removed
    (review finding B on PR #3, T-20260924-303164669) -- see the module
    docstring point 5. What replaced the "act on it" side is this: a
    finding is only ever marked `confirmed` once the SAME cpu reading has
    held across several separately-sampled cycle() calls."""

    def _finding(self, root_pid, cpu, cwd='C:/ws'):
        return {'root_pid': root_pid, 'root_ppid': 1, 'cwd': cwd,
                'tree_size': 1, 'age_seconds': 3600, 'cpu': cpu}

    def test_not_confirmed_before_min_streak_is_reached(self):
        state = {}
        for _ in range(2):
            findings = z.track_broker_idle_streaks([self._finding(10, cpu=42)], state,
                                                     min_streak=3)
        self.assertFalse(findings[0]['confirmed'])

    def test_confirmed_once_min_streak_of_unchanged_cpu_is_reached(self):
        state = {}
        for _ in range(3):
            findings = z.track_broker_idle_streaks([self._finding(10, cpu=42)], state,
                                                     min_streak=3)
        self.assertTrue(findings[0]['confirmed'])

    def test_a_cpu_change_resets_the_streak(self):
        state = {}
        z.track_broker_idle_streaks([self._finding(10, cpu=42)], state, min_streak=3)
        z.track_broker_idle_streaks([self._finding(10, cpu=42)], state, min_streak=3)
        # The broker did work between samples -- a real cpu change -- right
        # before what would have been the confirming third cycle.
        findings = z.track_broker_idle_streaks([self._finding(10, cpu=43)], state,
                                                min_streak=3)
        self.assertFalse(findings[0]['confirmed'])
        self.assertEqual(state[('C:/ws', 10)]['streak'], 1)

    def test_dropping_out_of_findings_loses_progress(self):
        """A candidate that stops being reported (process gone, or no
        longer superseded/idle) must not resume a stale streak later just
        because a coincidentally-matching cpu reading reappears."""
        state = {}
        z.track_broker_idle_streaks([self._finding(10, cpu=42)], state, min_streak=3)
        z.track_broker_idle_streaks([self._finding(10, cpu=42)], state, min_streak=3)
        z.track_broker_idle_streaks([], state, min_streak=3)  # candidate vanished
        findings = z.track_broker_idle_streaks([self._finding(10, cpu=42)], state,
                                                min_streak=3)
        self.assertFalse(findings[0]['confirmed'])
        self.assertEqual(state[('C:/ws', 10)]['streak'], 1)

    def test_different_cwds_track_independently(self):
        state = {}
        for _ in range(3):
            findings = z.track_broker_idle_streaks(
                [self._finding(10, cpu=42, cwd='C:/a'), self._finding(20, cpu=1, cwd='C:/b')],
                state, min_streak=3)
        self.assertTrue(all(f['confirmed'] for f in findings))
        self.assertEqual(len(state), 2)


if __name__ == '__main__':
    unittest.main()
