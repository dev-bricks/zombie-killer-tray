import dataclasses
import os
import subprocess
import sys
import time
import unittest
from pathlib import Path
from unittest.mock import patch

_SRC = str(Path(__file__).resolve().parent / "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

import zombie_killer_tray.killer as z


class FakeAPI:
    def __init__(self, rec):
        self.rec = rec
        self.dead = True
        self.killed = []
        self.closed = []
        self.reads = 0
        self.late_cpu = False

    def open(self, pid, terminate=False): return 'pinned-handle'
    def close(self, handle): self.closed.append(handle)
    def alive(self, handle): return True
    def parent_dead(self, pid): return self.dead
    def times(self, handle):
        self.reads += 1
        return self.rec.born, self.rec.cpu + int(self.late_cpu and self.reads > 1)

    def terminate(self, handle):
        self.killed.append(handle)
        return True

    def process_table(self):
        return []


class SafetyTests(unittest.TestCase):
    def setUp(self):
        self.r = z.Record(987654, 987653, int((time.time()-3600+11644473600)*1e7),
                          23, 'C:/bin/clangd.exe', ('clangd.exe',), 'language-server', True)
        self.api = FakeAPI(self.r)

    def test_stable_orphan_uses_same_handle(self):
        self.assertTrue(z.safe_terminate(self.api,self.r,self.r)[0])
        self.assertEqual(self.api.killed,['pinned-handle'])
        self.assertEqual(self.api.closed,['pinned-handle'])

    def test_live_parent_second_sample_blocks(self):
        self.assertFalse(z.safe_terminate(self.api,self.r,dataclasses.replace(self.r,parent_dead=False))[0])
        self.assertEqual(self.api.killed,[])

    def test_parent_reappears_before_kill_blocks(self):
        self.api.dead=False
        self.assertFalse(z.safe_terminate(self.api,self.r,self.r)[0])
        self.assertEqual(self.api.killed,[])

    def test_cpu_changed_between_samples_blocks(self):
        self.assertFalse(z.safe_terminate(self.api,self.r,dataclasses.replace(self.r,cpu=24))[0])

    def test_cpu_changed_at_final_handle_check_blocks(self):
        self.api.late_cpu=True
        self.assertFalse(z.safe_terminate(self.api,self.r,self.r)[0])
        self.assertEqual(self.api.killed,[])

    def test_pid_reused_between_samples_blocks(self):
        self.assertFalse(z.safe_terminate(self.api,self.r,dataclasses.replace(self.r,born=self.r.born+1))[0])

    def test_pid_reused_before_open_blocks(self):
        self.api.rec=dataclasses.replace(self.r,born=self.r.born+1)
        self.assertFalse(z.safe_terminate(self.api,self.r,self.r)[0])
        self.assertEqual(self.api.killed,[])

    def test_young_orphan_blocks(self):
        r=dataclasses.replace(self.r,born=int((time.time()+11644473600)*1e7))
        self.assertFalse(z.safe_terminate(self.api,r,r)[0])

    def test_unknown_parent_pid_blocks(self):
        r=dataclasses.replace(self.r,ppid=0)
        self.assertFalse(z.safe_terminate(self.api,r,r)[0])

    def test_non_targets(self):
        for exe,args in [
            ('C:/Windows/powershell.exe',['powershell.exe','mcp']),
            ('C:/node.exe',['node.exe','C:/test.js','ellmos-filecommander-mcp']),
            ('C:/python.exe',['python.exe','-c','print("mcp")']),
            ('C:/node.exe',['node.exe','C:/node_modules/ellmos-filecommander-mcp/test/test.js']),
            ('C:/node.exe',['node.exe','C:/node_modules/unknown-mcp/index.js']),
            # Same file name outside Antigravity's install location is not a target.
            ('C:/tools/language_server.exe',['language_server.exe','multicall','schedule','43 14 * * *']),
            # Near misses: wrong folder under the install, a subfolder below bin, the IDE's own session.
            (r'C:\Users\x\AppData\Local\Programs\Antigravity\resources\app\language_server.exe',
             ['language_server.exe','multicall','schedule','43 14 * * *']),
            (r'D:\Temp\Antigravity\resources\bin\evil\language_server.exe',
             ['language_server.exe','multicall','schedule','43 14 * * *']),
            (r'C:\Users\x\AppData\Local\Programs\Antigravity\resources\bin\language_server.exe',
             ['language_server.exe','--stdio']),
        ]:
            self.assertEqual(z.classify(exe,args),'')

    def test_real_entrypoint(self):
        self.assertEqual(z.classify('C:/node.exe',['node.exe','C:/node_modules/ellmos-filecommander-mcp/dist/index.js']),'mcp')
        self.assertEqual(z.classify('C:/node.exe',['node.exe','C:/node_modules/n8n-manager-mcp/dist/index.js']),'mcp')
        self.assertEqual(z.classify('C:/python.exe',['python.exe','-m','pylsp']),'language-server')
        self.assertEqual(z.classify(r'C:\Users\x\AppData\Local\Programs\Antigravity\resources\bin\language_server.exe',
            ['language_server.exe','multicall','schedule','43 14 * * *']),'language-server')

    def test_snapshot_inspects_antigravity_language_server(self):
        self.api.process_table=lambda:[(self.r.pid,self.r.ppid,'language_server.exe')]
        self.api.image=lambda h:r'C:\Users\x\AppData\Local\Programs\Antigravity\resources\bin\language_server.exe'
        with patch.object(z.psutil,'Process') as process:
            process.return_value.cmdline.return_value=['language_server.exe','multicall','schedule','43 14 * * *']
            records,_=z.snapshot(self.api)
        self.assertEqual(records[self.r.pid].kind,'language-server')

    def test_cycle_requires_two_samples(self):
        later=dataclasses.replace(self.r,cpu=24)
        with patch.object(z,'snapshot',side_effect=[({self.r.pid:self.r},{}),({later.pid:later},{})]), patch.object(z.time,'sleep'):
            self.assertEqual(z.cycle(self.api,apply=True),[])
        self.assertEqual(self.api.killed,[])

    def test_snapshot_skips_non_target_before_details(self):
        self.api.process_table=lambda:[(100,10,'powershell.exe'),(101,10,'chrome.exe')]
        with patch.object(z.psutil,'Process',side_effect=AssertionError('non-target details read')):
            self.assertEqual(z.snapshot(self.api),({},{}))

    def test_snapshot_discards_process_born_after_table_started(self):
        self.api.process_table=lambda:[(self.r.pid,self.r.ppid,'clangd.exe')]
        self.api.image=lambda h:'C:/bin/clangd.exe'
        self.api.rec=dataclasses.replace(self.r,born=int((time.time()+60+11644473600)*1e7))
        with patch.object(z.psutil,'Process') as process:
            process.return_value.cmdline.return_value=['clangd.exe']
            self.assertEqual(z.snapshot(self.api),({},{}))

    def test_snapshot_deadline_raises_without_partial_results(self):
        self.api.process_table=lambda:[(100,10,'node.exe')]
        with self.assertRaises(TimeoutError):
            z.snapshot(self.api,deadline=0)

    def test_stalled_cycle_never_mutates(self):
        with patch.object(z,'snapshot',return_value=({self.r.pid:self.r},{})), patch.object(z.time,'sleep'), patch.object(z.time,'monotonic',side_effect=[0,11]):
            self.assertEqual(z.cycle(self.api,apply=True),[])
        self.assertEqual(self.api.killed,[])

    def test_observation_gap_does_not_consume_scan_budget(self):
        clock = [0.0]

        def slow_snapshot(api, deadline=None):
            clock[0] += 3.5
            if clock[0] > deadline:
                raise TimeoutError('read-only process snapshot deadline exceeded')
            return {self.r.pid: self.r}, {}

        def observation_gap(seconds):
            clock[0] += seconds

        with patch.object(z, 'snapshot', side_effect=slow_snapshot), \
                patch.object(z.time, 'sleep', side_effect=observation_gap), \
                patch.object(z.time, 'monotonic', side_effect=lambda: clock[0]):
            outcomes = z.cycle(self.api, apply=True)

        self.assertEqual(clock[0], 9.0)  # Seven seconds of work plus the two-second gap.
        self.assertEqual(len(outcomes), 1)
        self.assertEqual(self.api.killed, ['pinned-handle'])

    def test_scan_work_exceeding_budget_still_aborts_without_kill(self):
        clock = [0.0]

        def stalled_snapshot(api, deadline=None):
            clock[0] += 4.5
            if clock[0] > deadline:
                raise TimeoutError('read-only process snapshot deadline exceeded')
            return {self.r.pid: self.r}, {}

        def observation_gap(seconds):
            clock[0] += seconds

        with patch.object(z, 'snapshot', side_effect=stalled_snapshot), \
                patch.object(z.time, 'sleep', side_effect=observation_gap), \
                patch.object(z.time, 'monotonic', side_effect=lambda: clock[0]), \
                self.assertRaises(TimeoutError):
            z.cycle(self.api, apply=True)

        self.assertEqual(self.api.killed, [])

    def test_failed_audit_prevents_kill(self):
        with patch.object(z,'snapshot',return_value=({self.r.pid:self.r},{})), patch.object(z.time,'sleep'), patch.object(z,'audit',side_effect=OSError('disk')), self.assertRaises(OSError):
            z.cycle(self.api,apply=True,audit_path='test-unused')
        self.assertEqual(self.api.killed,[])

    @unittest.skipUnless(os.name=='nt','Windows Win32 smoke')
    def test_owned_process_handle_smoke_and_live_parent(self):
        # Only this test's own newly spawned process is ever terminated.
        p=subprocess.Popen([sys.executable,'-c','import time; time.sleep(30)'],
                           creationflags=subprocess.CREATE_NO_WINDOW)
        api=z.Win32()
        h=None
        try:
            h=api.open(p.pid,terminate=True)
            self.assertTrue(h)
            self.assertTrue(api.alive(h))
            born,_cpu=api.times(h)
            self.assertGreater(born,0)
            self.assertFalse(api.parent_dead(os.getpid()))
            self.assertTrue(api.terminate(h))
            self.assertFalse(api.alive(h))
            p.wait(timeout=3)
        finally:
            if h:
                api.close(h)
            if p.poll() is None:
                p.kill()
                p.wait(timeout=3)


if __name__ == '__main__':
    unittest.main()


class WorkerSurvivalTests(unittest.TestCase):
    """A failing cycle must not end the watch worker (tray died with rc=1)."""

    def test_watch_logs_error_and_keeps_running(self):
        import tempfile
        from unittest import mock

        calls = {'n': 0}

        def flaky_cycle(*args, **kwargs):
            calls['n'] += 1
            if calls['n'] == 1:
                raise OSError('transient snapshot failure')
            raise SystemExit(0)  # stop the endless loop after the retry

        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(z, 'ROOT', Path(tmp)), \
                mock.patch.object(z, 'Win32', lambda: object()), \
                mock.patch.object(z, 'cycle', flaky_cycle), \
                mock.patch.object(z.time, 'sleep', lambda s: None), \
                mock.patch('sys.argv', ['zk', 'watch', '--interval', '3']):
            with self.assertRaises(SystemExit):
                z.main()
            self.assertEqual(calls['n'], 2)
            log = (Path(tmp) / 'zombie_worker_errors.log').read_text(encoding='utf-8')
            self.assertIn('transient snapshot failure', log)
