import importlib.util
import unittest
from pathlib import Path

path = Path(__file__).resolve().parents[1]/"scripts/analyze_frames.py"
spec = importlib.util.spec_from_file_location("analyze_frames", path)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class CadenceTests(unittest.TestCase):
    def setUp(self):
        self.frames = [10000+round(i*1e6/60) for i in range(289)]

    def test_60hz_full_span(self):
        r=m.analyze(self.frames, expected_span_ms=4800)
        self.assertTrue(r["accepted"])
        self.assertAlmostEqual(r["cadence_fps"],60)
        self.assertEqual(r["coverage_status"],"PASS")

    def test_missing_frame_rejected(self):
        frames=self.frames.copy();del frames[80]
        r=m.analyze(frames)
        self.assertFalse(r["accepted"])
        self.assertEqual(len(r["over_budget_intervals"]),1)

    def test_duplicate_and_wrap_rejected(self):
        for values in ("1,1,2", "100,200,0"):
            with self.assertRaises(ValueError):
                m.parse_frames("[SPLASH_FRAME_TIMES] us="+values,"splash")

    def test_all_runs_require_selection(self):
        log="[SPLASH_FRAME_TIMES] us=1,2,3\n[SPLASH_FRAME_TIMES] us=4,5,6"
        with self.assertRaises(ValueError):m.parse_frames(log,"splash")
        self.assertEqual(m.parse_frames(log,"splash",2),[4,5,6])

    def test_csv_and_log_same(self):
        csv="timestamp_us\n"+"\n".join(map(str,self.frames))
        log="[SPLASH_FRAME_TIMES] us="+",".join(map(str,self.frames))
        self.assertEqual(m.parse_frames(csv,"csv"),m.parse_frames(log,"splash"))

    def test_short_coverage_not_pass(self):
        self.assertFalse(m.analyze(self.frames[:60],expected_span_ms=4800)["accepted"])
        self.assertEqual(m.analyze(self.frames)["coverage_status"],"NOT_CHECKED")

    def test_no_average_hiding_long_short_pair(self):
        frames=self.frames.copy();frames[50]+=10000
        r=m.analyze(frames)
        self.assertAlmostEqual(r["cadence_fps"],60)
        self.assertFalse(r["accepted"])

    def test_invalid_parameters(self):
        for fps in (0,-1,float("nan"),float("inf")):
            with self.assertRaises(ValueError):m.analyze(self.frames,target_fps=fps)
        with self.assertRaises(ValueError):m.analyze(self.frames,expected_span_ms=-1)

    def test_malformed_record(self):
        for raw in ("", "[SPLASH_FRAME_TIMES] us=1,2,", "[SPLASH_FRAME_TIMES] us=1,2,x"):
            with self.assertRaises(ValueError):m.parse_frames(raw,"splash")

if __name__=="__main__":unittest.main()
