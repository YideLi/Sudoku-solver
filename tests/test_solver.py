"""Independent regression checks; not part of the three-file submission."""
import itertools
import random
import unittest

from sudoku_solver import (
    atom, build_general_kb, build_definite_kb, solve_full_grid_fc,
    solve_full_grid_bc, pl_bc_entails, backward_trace,
)
from logic_ import PropDefiniteKB, expr, Expr, pl_fc_entails, pl_true, parse_definite_clause


def closure(kb):
    """Small independent least-model oracle, used only by tests."""
    known = set()
    rules = [parse_definite_clause(c) for c in kb.clauses]
    while True:
        enlarged = known | {head for premises, head in rules if set(premises) <= known}
        if enlarged == known:
            return known
        known = enlarged


def make_kb(clauses):
    kb = PropDefiniteKB()
    for clause in clauses:
        kb.tell(expr(clause))
    return kb


class InferenceTests(unittest.TestCase):
    def test_cycle_without_support(self):
        kb = make_kb(['A ==> B', 'B ==> A'])
        self.assertFalse(pl_bc_entails(kb, expr('A')))
        self.assertFalse(pl_bc_entails(kb, expr('Unknown')))

    def test_cycle_with_later_alternative(self):
        # If B is permanently memoized False under active A, Q is lost.
        kb = make_kb(['B ==> A', 'A ==> B', 'C ==> A', '(A & B) ==> Q', 'C'])
        self.assertTrue(pl_bc_entails(kb, expr('Q')))

    def test_and_or_and_query_order(self):
        kb = make_kb(['A', '(A & B) ==> Q', 'C ==> Q', 'C'])
        self.assertFalse(pl_bc_entails(kb, expr('B')))
        self.assertTrue(pl_bc_entails(kb, expr('Q')))
        kb.retract(expr('C'))
        self.assertFalse(pl_bc_entails(kb, expr('Q')))

    def test_index_invalidation(self):
        kb = build_definite_kb(2, 1, 2, {})
        q = atom('Is', 1, 1, 1)
        self.assertFalse(pl_bc_entails(kb, q))
        kb.tell(q)
        self.assertTrue(pl_bc_entails(kb, q))
        self.assertTrue(pl_fc_entails(kb, q))
        kb.retract(q)
        self.assertFalse(pl_bc_entails(kb, q))
        self.assertFalse(pl_fc_entails(kb, q))

    def test_random_cyclic_kbs_against_independent_oracle(self):
        rng = random.Random(5005)
        symbols = [Expr(f'P{i}') for i in range(7)]
        for trial in range(200):
            kb = PropDefiniteKB()
            added = set()
            for symbol in symbols:
                if rng.random() < .2:
                    kb.tell(symbol)
            for _ in range(18):
                premises = rng.sample(symbols, rng.randint(1, 3))
                premise = premises[0] if len(premises) == 1 else Expr('&', *premises)
                clause = Expr('==>', premise, rng.choice(symbols))
                # The provided FC counts by clause value: duplicate rules
                # would incorrectly decrement the same counter twice.
                if clause not in added:
                    kb.tell(clause)
                    added.add(clause)
            expected = closure(kb)
            for symbol in symbols:
                self.assertEqual(pl_bc_entails(kb, symbol), symbol in expected, (trial, symbol))
                self.assertEqual(pl_fc_entails(kb, symbol), symbol in expected)

    def test_long_chain_without_recursion_limit(self):
        kb = PropDefiniteKB()
        kb.tell(Expr('P0'))
        for i in range(1500):
            kb.tell(Expr('==>', Expr(f'P{i}'), Expr(f'P{i + 1}')))
        self.assertTrue(pl_bc_entails(kb, Expr('P1500')))

    def test_trace_is_a_real_proof(self):
        kb = make_kb(['B ==> A', 'A ==> B', 'C ==> A', '(A & B) ==> Q', 'C'])
        verdict, trace, _ = backward_trace(kb, expr('Q'))
        self.assertTrue(verdict)
        seen = set()
        available = {(tuple(p), h) for p, h in map(parse_definite_clause, kb.clauses)}
        for step in trace:
            self.assertTrue(set(step['premises']) <= seen)
            self.assertIn((step['premises'], step['conclusion']), available)
            seen.add(step['conclusion'])
        self.assertEqual(trace[-1]['conclusion'], expr('Q'))

    def test_general_kb_models_exhaustive_2_by_2(self):
        kb = build_general_kb(2, 1, 2, {(1, 1): 1})
        symbols = [atom('Is', r, c, v) for r in [1, 2] for c in [1, 2] for v in [1, 2]]
        solutions = 0
        for values in itertools.product([False, True], repeat=8):
            model = dict(zip(symbols, values))
            legal = all(sum(model[atom('Is', r, c, v)] for v in [1, 2]) == 1
                        for r in [1, 2] for c in [1, 2])
            legal = legal and all(sum(model[atom('Is', r, c, v)] for c in [1, 2]) == 1
                                  for r in [1, 2] for v in [1, 2])
            legal = legal and all(sum(model[atom('Is', r, c, v)] for r in [1, 2]) == 1
                                  for c in [1, 2] for v in [1, 2])
            legal = legal and model[atom('Is', 1, 1, 1)]
            satisfied = all(pl_true(clause, model) for clause in kb.clauses)
            self.assertEqual(satisfied, legal)
            solutions += satisfied
        self.assertEqual(solutions, 1)

    def test_small_and_rectangular_boxes(self):
        for n, h, w in [(1, 1, 1), (2, 1, 2), (4, 2, 2), (6, 2, 3)]:
            solution = {(r + 1, c + 1): (r * w + r // h + c) % n + 1
                        for r in range(n) for c in range(n)}
            givens = {cell: v for cell, v in solution.items() if cell[1] != n}
            self.assertEqual(solve_full_grid_fc(n, h, w, givens), solution)
            self.assertEqual(solve_full_grid_bc(n, h, w, givens), solution)

    def test_invalid_and_underconstrained_inputs(self):
        for solver in [solve_full_grid_fc, solve_full_grid_bc]:
            with self.assertRaises(ValueError):
                solver(4, 2, 2, {})
            with self.assertRaises(ValueError):
                solver(4, 2, 2, {(1, 1): 1, (1, 2): 1})
        with self.assertRaises(ValueError):
            build_general_kb(9, 2, 3, {})


if __name__ == '__main__':
    unittest.main()
