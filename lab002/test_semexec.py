import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import semexec as S  # noqa: E402


def small_stream(mix="realistic", seed=3):
    table, edits = S.stream(seed, mix, steps=8, n=60)
    rows = table
    yield rows
    for e in edits:
        rows = S.apply_edit(rows, e)
        yield rows


def stale_count(ex_name, scn, mix="realistic", seed=3):
    ops, decl = S.scenario(scn)
    cls = S.EXECUTORS[ex_name]
    ex = cls(ops, decl, seed=seed) if ex_name.startswith("semantic") else cls(ops, decl)
    bad = 0
    for rows in small_stream(mix, seed):
        out = ex.step(rows)
        bad += sum(S.h(v) != S.h(fn(rows)) for n, (fn, _, _) in ops.items() for v in [out[n]])
    return bad, ex


class Baselines(unittest.TestCase):
    def test_baselines_never_stale(self):              # control C2
        for scn in ("true", "W3"):
            for ex in ("naive", "content", "content_sharded"):
                self.assertEqual(stale_count(ex, scn)[0], 0, (ex, scn))


class Controls(unittest.TestCase):
    def test_trusted_false_declaration_is_caught_by_evaluator(self):   # control C1
        bad, _ = stale_count("semantic_trusted", "W1", seed=7)  # stream with currency edits
        self.assertGreater(bad, 0)


class Verifier(unittest.TestCase):
    def rows(self):
        rng = random.Random(9)
        rows = S.make_table(rng, 60)
        return rows + [dict(r) for r in rows[:5]]          # include duplicates

    def test_accepts_true_declarations(self):
        ops, decl = S.scenario("true")
        v = S.SemanticVerified(ops, decl, seed=1)
        for name in ops:
            self.assertTrue(v.check(name, self.rows()), name)

    def test_rejects_false_declarations(self):
        for scn, op in (("W1", "usd_clean"), ("W2", "first_seen"), ("W4", "first_seen")):
            ops, decl = S.scenario(scn)
            v = S.SemanticVerified(ops, decl, seed=1)
            self.assertFalse(v.check(op, self.rows()), scn)

    def test_semantic_verified_true_scenario_never_stale(self):
        self.assertEqual(stale_count("semantic_verified", "true")[0], 0)


if __name__ == "__main__":
    unittest.main()
