# Sudoku, reason by reason

IT5005 assignment: propositional Sudoku knowledge representation, forward and backward inference, and an explanatory Streamlit interface.

## Run locally

Use Python 3.12 (the tested interpreter).

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run sudoku_app.py
```

On Windows, activate with `.venv\Scripts\activate` instead. The app locates `puzzles.json` relative to its own file. Its loader retains only givens; the solver never reads the reference solution.

## Files

- `sudoku_solver.py`: both KB encodings, the supplied FC engine with an indexed KB, an independent cycle-safe backward engine, full-grid solvers, and proof extraction.
- `sudoku_app.py`: puzzle selector, board, timed algorithm selection, cell queries and paginated natural-language proofs.
- `Sudoku_Assignment.ipynb`: experiments, exhaustive puzzle validation, all five conceptual answers, and references.
- `utils.py`, `logic_.py`, `puzzles.json`: unmodified course support files.
- `tests/`: regression tests, additional to the required submission.

## Inference design

General CNF encodes cell existence and uniqueness, peer exclusions and givens. Definite rules use explicit `Is` and `Not` atoms for same-cell/peer elimination and last-candidate deduction. The Horn encoding is a sound deduction system, not a logically equivalent rewrite of all Sudoku constraints. A puzzle outside the rule set's capability raises a clear error instead of being guessed or filled from the stored solution.

The full-grid FC solver calls the provided `pl_fc_entails` once with an unreachable sentinel to exhaust its agenda. A `PropDefiniteKB` subclass indexes premise lookups and observes facts processed by that unchanged routine. BC uses goal-driven AND/OR proof search with an explicit call stack, positive memoization within a query, path-cycle checks and temporary per-round failure caching. It retries when new positive proofs become available. It does not call FC. `tell` and `retract` invalidate KB indexes; use those methods rather than directly modifying `kb.clauses`.

Proof cards show actual supporting facts and fired rules. A False query is explained by a separately proved `Not` atom when available; failure to prove an atom alone is not treated as its negation.

## Validate

```bash
python -m unittest discover -s tests -v
```

For interactive notebook work:

```bash
python -m pip install notebook ipykernel
python -m notebook Sudoku_Assignment.ipynb
```

Run from the project directory. Run All performs two bounded 30-second experiments and checks all 729 cell/value queries in each of five puzzles with both inference algorithms. The complete notebook therefore takes several minutes. Its timeout subprocess code uses a POSIX resource guard when available; the wall-clock timeout remains the primary limit.

## Deploy from a private GitHub repository

1. Push the project to the requested **private** GitHub repository, including support files, `requirements.txt` and `.streamlit/config.toml`.
2. In Streamlit Community Cloud, connect that repository and select `sudoku_app.py` as the entrypoint, using Python 3.12.
3. Private repository access may require additional GitHub authorization. Keep the source repository private.
4. Check the deployed app and put its verified URL in the notebook's submission section. App viewer access is separate from repository privacy; arrange the required access for the marker.

Official documentation: [deploy an app](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy), [private repository access](https://docs.streamlit.io/deploy/streamlit-community-cloud/status).

## Course submission

Submit only `Sudoku_Assignment.ipynb`, `sudoku_solver.py`, and `sudoku_app.py` inside a ZIP folder named after the group. The deployment repository additionally needs the supporting files and dependencies. Do not submit `.venv`, tests, temporary experiments or development backups as part of the three-file course submission.

## References

- [AIMA Python](https://github.com/aimacode/aima-python): the knowledge-base and inference framework used by the supplied course modules.
- [AIPython, sections 5.3–5.4](https://artint.info/AIPython/): top-down proof structure and explanations. Our implementation adds explicit cycle handling and retries.
- [Norvig's Sudoku tutorial](https://www.norvig.com/sudoku.html): units, peers and elimination; its search engine is not used.
- [Sudoku as SAT](https://github.com/tyrelh/sudoku-as-sat): comparison with the CNF/SAT workflow.
- [Streamlit Sudoku](https://github.com/jhrcook/streamlit-sudoku): UI/solver separation; its Pyomo solver is not used.

The assignment implementation was written for the provided interfaces; external solver implementations were not copied into the submission.
