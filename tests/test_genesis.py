import copy
import unittest

from genesis.corpus import hidden_cases, public_cases
from genesis.evaluator import adjudicate, freeze_manifest, source_complexity, verify_freeze
from genesis.oracle import Oracle, same


class GenesisOracleTests(unittest.TestCase):
    def test_original_receipt_and_conflict_are_immutable(self):
        oracle = Oracle()
        first = {"op": "credit", "id": "a", "key": "x", "delta": 5}
        self.assertEqual(oracle.step(first), {"ok": True, "total": 5})
        oracle.step({"op": "credit", "id": "b", "key": "x", "delta": -2})
        self.assertEqual(oracle.step(first), {"ok": True, "total": 5})
        self.assertEqual(oracle.step({**first, "delta": 99}), {"ok": False, "error": "conflict"})
        self.assertEqual(oracle.step({"op": "balance", "key": "x"}), {"total": 3})

    def test_forward_reference_cycle_and_domain_separation(self):
        oracle = Oracle()
        child = {"op": "define", "id": "same", "parents": ["p"], "weight": 3}
        oracle.step(child)
        self.assertEqual(oracle.step({"op": "run"}), {"done": {}})
        oracle.step({"op": "credit", "id": "same", "key": "same", "delta": 7})
        oracle.step({"op": "define", "id": "p", "parents": [], "weight": 2})
        self.assertEqual(oracle.step({"op": "run"}), {"done": {"p": 2, "same": 5}})
        oracle.step({"op": "define", "id": "cycle", "parents": ["cycle"], "weight": 99})
        self.assertEqual(oracle.step({"op": "result", "id": "cycle"}), {"ready": False, "value": None})
        self.assertEqual(oracle.step({"op": "balance", "key": "same"}), {"total": 7})

    def test_response_equality_does_not_conflate_bool_and_int(self):
        self.assertFalse(same({"value": 1}, {"value": True}))
        self.assertTrue(same({"a": 1, "b": 2}, {"b": 2, "a": 1}))

    def test_corpus_is_deterministic_and_separated(self):
        self.assertEqual(hidden_cases(), hidden_cases())
        self.assertEqual(len(hidden_cases()), 6)
        public = {case["name"] for case in public_cases()}
        self.assertTrue(public.isdisjoint(case["name"] for case in hidden_cases()))
        self.assertTrue(all(len(case["messages"]) > 16 for case in hidden_cases()))


class GenesisEvaluationTests(unittest.TestCase):
    def trials(self, inventor_cpu=70, inventor_bytes=70, passed=True, latency=1):
        return [{"role": role, "repetition": rep, "result": {"passed": passed if role == "inventor" else True,
                 "metrics": {"cpu_usec": inventor_cpu if role == "inventor" else 100,
                             "checkpoint_bytes": inventor_bytes if role == "inventor" else 100,
                             "active_request_seconds": latency if role == "inventor" else 1}}}
                for rep in range(3) for role in ("baseline", "inventor")]

    def test_hypothesis_thresholds_and_gate_are_fixed(self):
        self.assertEqual(adjudicate(self.trials())["H2"], "supported_for_pair")
        self.assertEqual(adjudicate(self.trials(inventor_bytes=76))["H2"], "falsified_for_pair")
        self.assertEqual(adjudicate(self.trials(latency=1.11))["H2"], "falsified_for_pair")
        result = adjudicate(self.trials(passed=False))
        self.assertEqual(result["H1_inventor"], "falsified_for_submission")
        self.assertEqual(result["H2"], "ineligible_correctness_gate")
        self.assertIsNone(result["inventor_over_baseline"])

    def test_freeze_mismatch_stops_evaluation(self):
        manifest = freeze_manifest()
        verify_freeze(manifest)
        changed = dict(manifest); changed["HYPOTHESIS.md"] = "changed"
        with self.assertRaises(RuntimeError):
            verify_freeze(changed)

    def test_invalid_source_is_retained_as_failure_metadata(self):
        result = source_complexity("invalid source : !!!")
        self.assertFalse(result["syntax_valid"])
        self.assertGreater(result["source_bytes"], 0)


if __name__ == "__main__":
    unittest.main()
