"""Tests for the codex-broker detection added for T-20260924-303164669.

Covers: is_codex_broker() classification, broker_descendants() tree walk,
detect_superseded_idle_brokers() (read-only, TEIL A), kill_broker_tree()
(opt-in manual action), and -- critically -- that none of this feeds the
existing automatic eligible()/safe_terminate() kill path (Auflage
T-20260816-50: kill criterion stays exclusively "parent dead").
"""
import time
import unittest
from unittest.mock import patch

import zombie_killer as z

FILETIME_EPOCH = 11644473600


def ft(now_offset_seconds):
    return int((time.time() + now_offset_seconds + FILETIME_EPOCH) * 1e7)


class FakeMultiAPI:
    """Minimal multi-process fake keyed by pid; pid doubles as the handle."""

    def __init__(self, procs):
        # procs: {pid: {'ppid', 'name', 'born', 'cpu', 'exe', 'alive'}}
        self.procs = procs
        self.terminated = []

    def process_table(self):
        return [(pid, p['ppid'], p['name']) for pid, p in self.procs.items()]

    def open(self, pid, terminate=False):
        return pid if pid in self.procs else None

    def close(self, handle):
        pass

    def alive(self, handle):
        return bool(self.procs.get(handle, {}).get('alive'))

    def times(self, handle):
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
    """Stand-in for psutil.Process(pid).cmdline()."""

    def __init__(self, argv_by_pid):
        self.argv_by_pid = argv_by_pid

    def __call__(self, pid):
        inst = unittest.mock.Mock()
        inst.cmdline.return_value = self.argv_by_pid[pid]
        return inst


BROKER_EXE = 'C:/node.exe'
BROKER_ARGV = ['node.exe',
    'C:/Users/User/.claude/plugins/cache/openai-codex/codex/1.0.6/scripts/app-server-broker.mjs']


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
        table = [(1, 0, 'node.exe'), (2, 1, 'child.exe'), (3, 2, 'grandchild.exe'),
                 (99, 0, 'unrelated.exe')]
        self.assertEqual(z.broker_descendants(table, 1), {1, 2, 3})


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

    def _snap(self, api, argv_map):
        """broker_snapshot() taken THIS instant, matching production timing
        (cpu is summed live, immediately -- see broker_snapshot docstring)."""
        with patch.object(z.psutil, 'Process', FakeCmdline(argv_map)):
            return z.broker_snapshot(api, api.process_table())

    def test_lone_broker_is_never_a_candidate(self):
        procs = {20: self._procs(-1000, 0)[20]}
        api = FakeMultiAPI(procs)
        rows = self._snap(api, {20: BROKER_ARGV})
        findings = z.detect_superseded_idle_brokers(rows, rows)
        self.assertEqual(findings, [])

    def test_superseded_idle_old_broker_is_flagged(self):
        procs = self._procs(old_born_offset=-3600, old_cpu=42)
        api = FakeMultiAPI(procs)
        argv_map = {10: BROKER_ARGV, 20: BROKER_ARGV}
        rows = self._snap(api, argv_map)  # nothing changed -> same rows twice is fine
        findings = z.detect_superseded_idle_brokers(rows, rows, min_idle_seconds=600)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]['root_pid'], 10)
        self.assertEqual(findings[0]['tree_size'], 2)  # broker + its python child
        self.assertGreaterEqual(findings[0]['age_seconds'], 3599)

    def test_still_current_broker_is_never_flagged(self):
        procs = self._procs(old_born_offset=-3600, old_cpu=42)
        api = FakeMultiAPI(procs)
        argv_map = {10: BROKER_ARGV, 20: BROKER_ARGV}
        rows = self._snap(api, argv_map)
        findings = z.detect_superseded_idle_brokers(rows, rows, min_idle_seconds=600)
        self.assertNotIn(20, [f['root_pid'] for f in findings])

    def test_active_old_broker_is_not_flagged(self):
        procs = self._procs(old_born_offset=-3600, old_cpu=42)
        api = FakeMultiAPI(procs)
        argv_map = {10: BROKER_ARGV, 20: BROKER_ARGV}
        before = self._snap(api, argv_map)
        procs[11]['cpu'] += 3  # child did work between the two samples
        after = self._snap(api, argv_map)
        findings = z.detect_superseded_idle_brokers(before, after, min_idle_seconds=600)
        self.assertEqual(findings, [])

    def test_too_young_superseded_broker_is_not_flagged(self):
        procs = self._procs(old_born_offset=-30, old_cpu=42)  # only 30s old
        api = FakeMultiAPI(procs)
        argv_map = {10: BROKER_ARGV, 20: BROKER_ARGV}
        rows = self._snap(api, argv_map)
        findings = z.detect_superseded_idle_brokers(rows, rows, min_idle_seconds=600)
        self.assertEqual(findings, [])

    def test_exited_between_samples_is_not_flagged(self):
        procs = self._procs(old_born_offset=-3600, old_cpu=42)
        api = FakeMultiAPI(procs)
        before = self._snap(api, {10: BROKER_ARGV, 20: BROKER_ARGV})
        del api.procs[10]  # gone in the second sample
        after = self._snap(api, {20: BROKER_ARGV})
        findings = z.detect_superseded_idle_brokers(before, after, min_idle_seconds=600)
        self.assertEqual(findings, [])


class KillBrokerTreeTests(unittest.TestCase):
    def test_refuses_to_kill_a_pid_that_is_not_a_verified_candidate(self):
        api = FakeMultiAPI({20: {'ppid': 1, 'name': 'node.exe', 'born': ft(-5),
                                  'cpu': 1, 'exe': BROKER_EXE, 'alive': True}})
        with patch.object(z.psutil, 'Process', FakeCmdline({20: BROKER_ARGV})), \
             patch.object(z.time, 'sleep'):
            killed, reason = z.kill_broker_tree(api, root_pid=10)
        self.assertEqual(killed, [])
        self.assertEqual(reason, 'not-a-verified-candidate')
        self.assertEqual(api.terminated, [])

    def test_kills_children_before_root_for_a_verified_candidate(self):
        procs = {
            10: {'ppid': 1, 'name': 'node.exe', 'born': ft(-3600), 'cpu': 42,
                 'exe': BROKER_EXE, 'alive': True},
            11: {'ppid': 10, 'name': 'python.exe', 'born': ft(-3599), 'cpu': 5,
                 'exe': 'C:/python.exe', 'alive': True},
            20: {'ppid': 1, 'name': 'node.exe', 'born': ft(-5), 'cpu': 1,
                 'exe': BROKER_EXE, 'alive': True},
        }
        api = FakeMultiAPI(procs)
        with patch.object(z.psutil, 'Process', FakeCmdline({10: BROKER_ARGV, 20: BROKER_ARGV})), \
             patch.object(z.time, 'sleep'):
            killed, reason = z.kill_broker_tree(api, root_pid=10, min_idle_seconds=600)
        self.assertEqual(reason, 'killed')
        self.assertEqual(killed, [11, 10])  # child before root
        self.assertEqual(api.terminated, [11, 10])
        self.assertTrue(api.procs[20]['alive'])  # the CURRENT broker is untouched


if __name__ == '__main__':
    unittest.main()
