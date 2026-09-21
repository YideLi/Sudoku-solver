"""IT5005: propositional Sudoku representation and inference.

Only the supplied modules are imported. General CNF and definite-clause
reasoning are separate encodings; neither reads a stored puzzle solution.
See the notebook for derivations, experiments and reference acknowledgements.
"""

from utils import *
from logic_ import *


# Do not change this function; it is used to create atomic propositions.
def atom(prefix, r, c, v):
    """prefix is 'Is' or 'Not'. Returns the Expr for e.g. Is3_2_4."""
    return expr(f'{prefix}{r}_{c}_{v}')


def _validate(n, box_h, box_w, givens):
    if any(type(x) is not int or x < 1 for x in (n, box_h, box_w)):
        raise ValueError('Grid and box dimensions must be positive integers.')
    if box_h * box_w != n or n % box_h or n % box_w:
        raise ValueError('Boxes must tile the grid and contain n cells.')
    for cell, value in givens.items():
        if (not isinstance(cell, tuple) or len(cell) != 2
                or any(type(x) is not int or not 1 <= x <= n
                       for x in (*cell, value))):
            raise ValueError('Givens must map (row, column) to values in 1..n.')
    for unit in _units(n, box_h, box_w):
        values = [givens[cell] for cell in unit if cell in givens]
        if len(values) != len(set(values)):
            raise ValueError('Conflicting givens in a row, column or box.')


def _units(n, box_h, box_w):
    rows = [[(r, c) for c in range(1, n + 1)] for r in range(1, n + 1)]
    cols = [[(r, c) for r in range(1, n + 1)] for c in range(1, n + 1)]
    boxes = [[(r, c) for r in range(top, top + box_h)
              for c in range(left, left + box_w)]
             for top in range(1, n + 1, box_h)
             for left in range(1, n + 1, box_w)]
    return rows + cols + boxes


def _peers(n, box_h, box_w):
    peers = {(r, c): set() for r in range(1, n + 1) for c in range(1, n + 1)}
    for unit in _units(n, box_h, box_w):
        for cell in unit:
            peers[cell].update(unit)
    return {cell: sorted(others - {cell}) for cell, others in peers.items()}


class _IndexedDefiniteKB(PropDefiniteKB):
    """Keep AIMA's FC unchanged, but index premise lookups.

    The optional processed set observes facts the supplied algorithm actually
    processes. It is used to collect its full deductive closure.
    """

    def __init__(self):
        super().__init__()
        self._premise_index = None
        self._proof_index = None
        self.processed = None

    def tell(self, sentence):
        super().tell(sentence)
        self._premise_index = None
        self._proof_index = None

    def retract(self, sentence):
        super().retract(sentence)
        self._premise_index = None
        self._proof_index = None

    def clauses_with_premise(self, p):
        if self._premise_index is None:
            self._premise_index = {}
            for clause in self.clauses:
                if clause.op == '==>':
                    for premise in set(conjuncts(clause.args[0])):
                        self._premise_index.setdefault(premise, []).append(clause)
        if self.processed is not None:
            self.processed.add(p)
        return self._premise_index.get(p, [])


def build_general_kb(n, box_h, box_w, givens):
    """Return a PropKB with cell existence, uniqueness, peers and givens."""
    _validate(n, box_h, box_w, givens)
    kb = PropKB()
    peers = _peers(n, box_h, box_w)
    symbols = {(r, c, v): atom('Is', r, c, v)
               for r, c in peers for v in range(1, n + 1)}
    for r, c in peers:
        kb.tell(associate('|', [symbols[r, c, v] for v in range(1, n + 1)]))
        for v in range(1, n + 1):
            for w in range(v + 1, n + 1):
                kb.tell(~symbols[r, c, v] | ~symbols[r, c, w])
        for rr, cc in peers[r, c]:
            if (r, c) < (rr, cc):
                for v in range(1, n + 1):
                    kb.tell(~symbols[r, c, v] | ~symbols[rr, cc, v])
    for (r, c), v in sorted(givens.items()):
        kb.tell(symbols[r, c, v])
    return kb


def build_definite_kb(n, box_h, box_w, givens):
    """Return Horn rules for elimination and a cell's last candidate.

    Not is an explicit positive atom, not logical negation. These rules are
    sound Sudoku deductions, not a model-equivalent Horn rewrite of CNF.
    """
    _validate(n, box_h, box_w, givens)
    kb = _IndexedDefiniteKB()
    peers = _peers(n, box_h, box_w)
    yes = {(r, c, v): atom('Is', r, c, v)
           for r, c in peers for v in range(1, n + 1)}
    no = {(r, c, v): atom('Not', r, c, v)
          for r, c in peers for v in range(1, n + 1)}
    for (r, c), v in sorted(givens.items()):
        kb.tell(yes[r, c, v])
    for r, c in peers:
        for v in range(1, n + 1):
            for w in range(1, n + 1):
                if w != v:
                    kb.tell(Expr('==>', yes[r, c, v], no[r, c, w]))
            for rr, cc in peers[r, c]:
                kb.tell(Expr('==>', yes[r, c, v], no[rr, cc, v]))
            excluded = [no[r, c, w] for w in range(1, n + 1) if w != v]
            kb.tell(Expr('==>', associate('&', excluded), yes[r, c, v])
                    if excluded else yes[r, c, v])
    return kb


def _check_grid(n, box_h, box_w, givens, grid):
    if len(grid) != n * n:
        raise ValueError('The elimination rules cannot determine every cell; no guess was made.')
    expected = set(range(1, n + 1))
    if (any({grid[cell] for cell in unit} != expected
            for unit in _units(n, box_h, box_w))
            or any(grid[cell] != value for cell, value in givens.items())):
        raise ValueError('The deductions do not form a consistent Sudoku solution.')
    return grid


def solve_full_grid_fc(n, box_h, box_w, givens):
    """Collect closure in one shared run of the supplied pl_fc_entails.

    A fresh, unreachable query forces the existing FC agenda to exhaustion.
    The indexed KB observes processed facts; it does not infer anything itself.
    """
    kb = build_definite_kb(n, box_h, box_w, givens)
    kb.processed = set()
    pl_fc_entails(kb, Expr('SudokuClosureSentinel'))
    grid = {}
    for r in range(1, n + 1):
        for c in range(1, n + 1):
            values = [v for v in range(1, n + 1) if atom('Is', r, c, v) in kb.processed]
            if len(values) > 1:
                raise ValueError('Contradictory values were derived for a cell.')
            if values:
                grid[r, c] = values[0]
    return _check_grid(n, box_h, box_w, givens, grid)


def _proof_index(kb):
    if isinstance(kb, _IndexedDefiniteKB) and kb._proof_index is not None:
        return kb._proof_index
    rules, facts = {}, set()
    for clause in kb.clauses:
        premises, head = parse_definite_clause(clause)
        if not premises:
            facts.add(head)
        else:
            rules.setdefault(head, []).append(tuple(dict.fromkeys(premises)))
    if isinstance(kb, _IndexedDefiniteKB):
        kb._proof_index = rules, facts
    return rules, facts


def _backward(kb, query, record=False):
    """Goal-driven AND/OR search, with positive tabling and retries.

    Explicit frames implement recursion without Python's recursion limit.
    A cycle blocks only its branch. Failed goals are cached for one round
    only, then retried if a new positive proof was found. Caches are local
    to this query and KB snapshot; a cycle is never evidence for a fact.
    """
    rules, facts = _proof_index(kb)
    proven = set(facts)
    reasons = {fact: () for fact in facts} if record else {}
    rounds = 0
    while query not in proven:
        rounds += 1
        before = len(proven)
        failed = set()
        active = {query}
        # Frame = [goal, alternative-rule index, next-premise index].
        stack = [[query, 0, 0]]
        while stack:
            goal, ri, pi = stack[-1]
            options = rules.get(goal, ())
            if goal in proven or ri == len(options):
                if goal not in proven:
                    failed.add(goal)
                active.remove(goal)
                stack.pop()
                continue
            premises = options[ri]
            if pi == len(premises):
                proven.add(goal)
                if record:
                    reasons[goal] = premises
                continue
            premise = premises[pi]
            if premise in proven:
                stack[-1][2] += 1
            elif premise in active or premise in failed:
                stack[-1][1] += 1
                stack[-1][2] = 0
            else:
                active.add(premise)
                stack.append([premise, 0, 0])
        if len(proven) == before:
            break
    return query in proven, reasons, rounds


def pl_bc_entails(kb, query):
    """Return whether a finite propositional definite KB entails query."""
    return _backward(kb, query)[0]


def backward_trace(kb, query):
    """Return verdict and an actual premises-before-conclusion proof.

    Uses the same engine as pl_bc_entails; unproved queries have no positive
    proof and return an empty trace. The app can separately query Not.
    """
    verdict, reasons, rounds = _backward(kb, query, record=True)
    if not verdict:
        return False, [], rounds
    ordered = []
    seen = set()
    stack = [(query, False)]
    while stack:
        goal, ready = stack.pop()
        if goal in seen:
            continue
        if ready:
            seen.add(goal)
            ordered.append({'conclusion': goal, 'premises': reasons[goal]})
        else:
            stack.append((goal, True))
            stack.extend((p, False) for p in reversed(reasons[goal]))
    return True, ordered, rounds


def solve_full_grid_bc(n, box_h, box_w, givens):
    """Prove candidates one cell at a time using independent BC queries."""
    kb = build_definite_kb(n, box_h, box_w, givens)
    grid = {}
    for r in range(1, n + 1):
        for c in range(1, n + 1):
            for v in range(1, n + 1):
                if pl_bc_entails(kb, atom('Is', r, c, v)):
                    grid[r, c] = v
                    break
    return _check_grid(n, box_h, box_w, givens, grid)
