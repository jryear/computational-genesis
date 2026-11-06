import concurrent.futures
import json
from pathlib import Path
import sys
import subprocess
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from substrate import Runtime, Refusal
from oracle import grade
from fixtures import records


def transition(rev=0, op="normalize", target="normalized", ident="one"):
    return {"request_id": ident, "expected_revision": rev, "capability": op, "target": target}


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = str(Path(self.temp.name) / "state.db")
        self.runtime = Runtime(self.path)

    def tearDown(self):
        self.runtime.close(); self.temp.cleanup()

    def test_replay_persists_after_restart(self):
        receipt = self.runtime.transition(transition())
        self.runtime.close(); self.runtime = Runtime(self.path)
        self.assertEqual(self.runtime.transition(transition()), receipt)
        self.assertEqual(self.runtime.state()["remaining"], 11)

    def test_request_identity_cannot_change(self):
        self.runtime.transition(transition())
        with self.assertRaisesRegex(Refusal, "identity_conflict"):
            self.runtime.transition(transition(1, "aggregate", "aggregated"))

    def test_bad_dependency_and_stale_state_do_not_mutate(self):
        before = self.runtime.state()
        for req in (transition(0, "aggregate", "aggregated"), transition(1), transition(target="verified")):
            with self.assertRaises(Refusal):
                self.runtime.transition(req)
            self.assertEqual(before, self.runtime.state())

    def test_supervisor_pause(self):
        self.runtime.pause(True)
        with self.assertRaisesRegex(Refusal, "paused"):
            self.runtime.transition(transition())
        self.runtime.pause(False)
        self.runtime.transition(transition())

    def test_noop_and_exhaustion(self):
        self.runtime.transition(transition())
        for i in range(1, 12):
            result = self.runtime.transition(transition(i, ident="noop" + str(i)))
            self.assertEqual(result["route"], "already_satisfied")
        with self.assertRaisesRegex(Refusal, "budget_exhausted"):
            self.runtime.transition(transition(12, ident="exhausted"))
        self.assertEqual(self.runtime.state()["work_units"], 1)

    def test_candidate_cannot_escape_grammar(self):
        for plan in (["shell"], ["verify", "normalize"], ["normalize"] * 999):
            with self.assertRaises(Refusal):
                self.runtime.propose("p_test", plan)
        with self.assertRaises(Refusal):
            self.runtime.propose("../../escape", ["normalize", "aggregate", "verify"])

    def test_composition_qualified_and_verified(self):
        proof = self.runtime.propose("p_test", ["normalize", "aggregate", "verify"])
        self.assertTrue(proof["retained"])
        self.assertIsNone(proof["latency_improvement"])
        result = self.runtime.transition(transition(0, "p_test", "verified"))
        self.assertTrue(grade(records(), result["result"]))
        self.assertEqual(self.runtime.state()["work_units"], 3)

    def test_multiple_inputs_match_independent_oracle(self):
        for seed in range(20):
            runtime = Runtime(str(Path(self.temp.name) / (str(seed) + ".db")), seed=seed)
            try:
                for rev, (op, target) in enumerate(zip(("normalize", "aggregate", "verify"), ("normalized", "aggregated", "verified"))):
                    runtime.transition(transition(rev, op, target, "s" + str(rev)))
                self.assertTrue(grade(records(seed), runtime.observe()["result"]))
            finally:
                runtime.close()

    def test_concurrent_claims_have_one_winner(self):
        def write(i):
            runtime = Runtime(self.path)
            try:
                return runtime.transition(transition(ident="claim" + str(i)))
            except Refusal:
                return None
            finally:
                runtime.close()
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(write, range(2)))
        self.assertEqual(sum(r is not None for r in results), 1)
        self.assertEqual(self.runtime.state()["revision"], 1)

    def test_public_observation_has_no_os_metadata(self):
        public = json.dumps(self.runtime.observe())
        for term in ("/", "pid", "command", "process", "file", "application"):
            self.assertNotIn(term, public)

    def test_process_death_rolls_back_uncommitted_checkpoint(self):
        script = """
import os, sys
from substrate import Runtime, canonical
r=Runtime(sys.argv[1])
r.db.execute('BEGIN IMMEDIATE')
s=r.state(); s['revision']=999
r.db.execute('UPDATE state SET payload=? WHERE id=1',(canonical(s),))
os._exit(91)
"""
        result = subprocess.run([sys.executable, "-c", script, self.path], env={"PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src")})
        self.assertEqual(result.returncode, 91)
        self.assertEqual(self.runtime.observe()["revision"], 0)
        self.runtime.transition(transition())

    def test_partial_composition_honors_dependency(self):
        self.runtime.propose("p_finish", ["aggregate", "verify"])
        with self.assertRaisesRegex(Refusal, "dependency"):
            self.runtime.transition(transition(0, "p_finish", "verified"))
        self.runtime.transition(transition())
        result = self.runtime.transition(transition(1, "p_finish", "verified", "finish"))
        self.assertTrue(grade(records(), result["result"]))

    def test_primitive_identity_cannot_change(self):
        first = self.runtime.propose("p_test", ["normalize", "aggregate"])
        self.assertEqual(self.runtime.propose("p_test", ["normalize", "aggregate"]), first)
        with self.assertRaisesRegex(Refusal, "primitive_identity_conflict"):
            self.runtime.propose("p_test", ["normalize", "aggregate", "verify"])


if __name__ == "__main__":
    unittest.main()
