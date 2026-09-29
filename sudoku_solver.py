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

def build_general_kb(n, box_h, box_w, givens):
    """Return a PropKB encoding this n x n Sudoku's constraints plus the given
        cells, as general clauses.
    
        Parameters
        ----------
        n, box_h, box_w : int
        givens : dict[(int, int), int]
    
        Returns
        -------
        PropKB
        """
    kb = PropKB()
    # Rule1: Every cell has at least one value from {1, . . . , n}
    for i in range(1,n+1):
        for j in range(1,n+1):
            clause = atom("Is",i,j,1)
            for k in range(2,n+1):
                clause = clause | atom("Is",i,j,k)
            kb.tell(clause)
    # Rule2: Every cell has at most one value from {1, . . . , n}. 
    for i in range(1,n+1):
        for j in range(1,n+1):
            for k in range(1,n+1):
                for m in range(k+1,n+1):
                    clause = ~atom("Is",i,j,k) | ~atom("Is",i,j,m)
                    kb.tell(clause)
    # Rule3: No two cells in the same row hold the same value.
    for i in range(1,n+1):
        for k in range(1,n+1):
            for j in range(1,n+1):
                for m in range(j+1,n+1):
                    clause = ~atom("Is",i,j,k) | ~atom("Is",i,m,k)
                    kb.tell(clause)
    # Rule4: No two cells in the same column hold the same value.
    for j in range(1,n+1):
        for k in range(1,n+1):
            for i in range(1,n+1):
                for m in range(i+1,n+1):
                    clause = ~atom("Is",i,j,k) | ~atom("Is",m,j,k)
                    kb.tell(clause)
    # Rule5: No two cells in the same box hold the same value.
    for box_i in range(1,n+1,box_h):
        for box_j in range(1,n+1,box_w):
            cells = []
            for i in range(box_i,box_i+box_h):
                for j in range(box_j,box_j+box_w):
                    cells.append((i,j))
            for k in range(1,n+1):
                for x in range(len(cells)):
                    for y in range(x+1,len(cells)):
                        i,j = cells[x]
                        m,p = cells[y]
                        clause = ~atom("Is",i,j,k) | ~atom("Is",m,p,k)
                        kb.tell(clause)
    # Rule6: The givens cells hold their stated values.
    for (i,j),k in givens.items():
        kb.tell(atom("Is",i,j,k))
    return kb


def build_definite_kb(n, box_h, box_w, givens):
    """Return a PropDefiniteKB encoding this n x n Sudoku's constraints plus
        the given cells, using elimination + last-candidate reasoning.
    
        Parameters
        ----------
        n, box_h, box_w : int
        givens : dict[(int, int), int] -- {(row, col): value}, 1-indexed
    
        Returns
        -------
        PropDefiniteKB
        """
    definite_kb = PropDefiniteKB()
    # Rule1: Every cell has at least one value from {1, . . . , n}
    for i in range(1,n+1):
        for j in range(1,n+1):
            for k in range(1,n+1):
                clause = None
                for m in range(1,n+1):
                    if m != k:
                        if clause is None:
                            clause = atom("Not",i,j,m)
                        else:
                            clause = clause & atom("Not",i,j,m)
                if clause is None:
                    definite_kb.tell(atom("Is",i,j,k))
                else:
                    definite_kb.tell(clause |'==>'| atom("Is",i,j,k))
    # Rule2: Every cell has at most one value from {1, . . . , n}. (no cell holds two digits at once)
    for i in range(1,n+1):
        for j in range(1,n+1):
            for k in range(1,n+1):
                for m in range(1,n+1):
                    if k != m:
                        clause = atom("Is",i,j,k) |'==>'| atom("Not",i,j,m)
                        definite_kb.tell(clause)
    # Rule3: No two cells in the same row hold the same value.
    for i in range(1,n+1):
        for j in range(1,n+1):
            for k in range(1,n+1):
                for m in range(1,n+1):
                    if j != m:
                        clause = atom("Is",i,j,k) |'==>'| atom("Not",i,m,k)
                        definite_kb.tell(clause)
    # Rule4: No two cells in the same column hold the same value.
    for i in range(1,n+1):
        for j in range(1,n+1):
            for k in range(1,n+1):
                for m in range(1,n+1):
                    if i != m:
                        clause = atom("Is",i,j,k) |'==>'| atom("Not",m,j,k)
                        definite_kb.tell(clause)
    # Rule5: No two cells in the same box hold the same value.(No repeating rules)
    for box_i in range(1,n+1,box_h):
        for box_j in range(1,n+1,box_w):
            for i in range(box_i,box_i+box_h):
                for j in range(box_j,box_j+box_w):
                    for k in range(1,n+1):
                        for m in range(box_i,box_i+box_h):
                            for p in range(box_j,box_j+box_w):
                                if i != m and j != p:
                                    clause = atom("Is",i,j,k) |'==>'| atom("Not",m,p,k)
                                    definite_kb.tell(clause)
    # Rule6: The givens cells hold their stated values.
    for (i,j),k in givens.items():
        definite_kb.tell(atom("Is",i,j,k))
    return definite_kb


def forward_chain_closure(kb):
    # Help Function to reduce repeating
    premise_index = {}
    for clause in kb.clauses:
        if clause.op == "==>":
            for premise in conjuncts(clause.args[0]):
                if premise not in premise_index:
                    premise_index[premise] = []
                premise_index[premise].append(clause)
    closure = set()

    def find_rules(premise):
        closure.add(premise)
        return premise_index.get(premise,[])

    kb.clauses_with_premise = find_rules

    sentinel = expr("ForwardClosureComplete")
    pl_fc_entails(kb,sentinel)

    return closure

def solve_full_grid_fc(n, box_h, box_w, givens):
    """Solve the whole puzzle using build_definite_kb + pl_fc_entails.
    Returns
    -------
    dict[(int, int), int] -- {(row, col): value} for every cell
    """
    kb = build_definite_kb(n,box_h,box_w,givens)
    closure = forward_chain_closure(kb)
    solved_grid = givens.copy()

    for i in range(1,n+1):
        for j in range(1,n+1):
            if (i,j) not in givens:
                for k in range(1,n+1):
                    query = atom("Is",i,j,k)

                    if query in closure:
                        solved_grid[(i,j)] = k
                        break
    return solved_grid


def _backward(kb,query):
    """Run backward chaining and record successful supporting rules."""

    if not hasattr(kb,"bc_facts") or not hasattr(kb,"bc_reasons"):
        kb.bc_facts = set()
        kb.bc_rules = {}

        for clause in kb.clauses:
            premises,conclusion = parse_definite_clause(clause)

            if len(premises) == 0:
                kb.bc_facts.add(conclusion)
            else:
                if conclusion not in kb.bc_rules:
                    kb.bc_rules[conclusion] = []

                kb.bc_rules[conclusion].append(tuple(premises))
        kb.bc_proved = set(kb.bc_facts)
        # Facts have no supporting premises.
        kb.bc_reasons = {
            fact: () for fact in kb.bc_facts
        }
    rounds = 0

    while query not in kb.bc_proved:
        rounds += 1
        proved_before = len(kb.bc_proved)
        failed = set()
        checking = set()
        def prove(goal):
            if goal in kb.bc_proved:
                return True

            if goal in failed:
                return False

            if goal in checking:
                return False
            checking.add(goal)
            for premises in kb.bc_rules.get(goal,[]):
                rule_proved = True
                for premise in premises:
                    if not prove(premise):
                        rule_proved = False
                        break
                if rule_proved:
                    checking.remove(goal)
                    kb.bc_proved.add(goal)
                    kb.bc_reasons[goal] = premises

                    return True
            checking.remove(goal)
            failed.add(goal)
            return False
        prove(query)
        if len(kb.bc_proved) == proved_before:
            break

    return query in kb.bc_proved,rounds


def pl_bc_entails(kb,query):
    """Return True when backward chaining proves the query."""
    verdict,rounds = _backward(kb,query)
    return verdict


def backward_trace(kb,query):
    """Return the result and its premises-before-conclusion proof trace."""
    verdict,rounds = _backward(kb,query)

    if not verdict:
        return False,[],rounds
    trace = []
    seen = set()
    def add_step(goal):
        if goal in seen:
            return

        premises = kb.bc_reasons[goal]

        # Add all supporting premises before their conclusion.
        for premise in premises:
            add_step(premise)

        seen.add(goal)

        trace.append({
            "conclusion": goal,
            "premises": premises
        })
    add_step(query)
    return True,trace,rounds


def solve_full_grid_bc(n, box_h, box_w, givens):
    """Solve the whole puzzle using build_definite_kb + your own pl_bc_entails.

    For each cell, try each candidate value until pl_bc_entails confirms one
    -- the same per-cell strategy as solve_full_grid_fc, but backed by
    backward chaining instead of a single shared forward-chaining pass.

    Returns
    -------
    dict[(int, int), int] -- {(row, col): value} for every cell
    """
    kb = build_definite_kb(n,box_h,box_w,givens)
    solved_grid = givens.copy()

    for i in range(1,n+1):
        for j in range(1,n+1):
            if (i,j) not in givens:
                for k in range(1,n+1):
                    query = atom("Is",i,j,k)
                    if pl_bc_entails(kb,query):
                        solved_grid[(i,j)] = k
                        break
    return solved_grid
