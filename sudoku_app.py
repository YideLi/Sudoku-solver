"""Streamlit interface; every deduction comes from sudoku_solver.py."""

import json
from pathlib import Path
from time import perf_counter

import streamlit as st

from sudoku_solver import (
    atom,
    build_definite_kb,
    build_general_kb,
    solve_full_grid_fc,
    solve_full_grid_bc,
    pl_bc_entails,
    backward_trace,
)


st.set_page_config(page_title='Sudoku | Reason by reason', page_icon='🧩', layout='wide')


@st.cache_data
def load_puzzles():
    """The UI deliberately loads givens only, never the reference solution."""
    raw = json.loads(Path(__file__).with_name('puzzles.json').read_text())
    puzzles = [
        {tuple(map(int, key.split('_'))): value for key, value in item['givens'].items()}
        for item in raw['puzzles']
    ]
    return raw['n'], raw['box_h'], raw['box_w'], puzzles


def board_html(n, box_h, box_w, givens, values, highlight=None):
    rows = []
    for r in range(1, n + 1):
        cells = []
        for c in range(1, n + 1):
            value = values.get((r, c), '')
            classes = ['given' if (r, c) in givens else 'deduced']
            if c % box_w == 0 and c < n:
                classes.append('box-right')
            if r % box_h == 0 and r < n:
                classes.append('box-bottom')
            if highlight == (r, c):
                classes.append('selected')
            label = f'Row {r}, column {c}: {value or "empty"}'
            cells.append(f'<td class="{" ".join(classes)}" aria-label="{label}">{value}</td>')
        rows.append('<tr>' + ''.join(cells) + '</tr>')
    return '<table class="sudoku-board" aria-label="Sudoku board">' + ''.join(rows) + '</table>'


def decode(symbol):
    name = symbol.op
    prefix = 'Not' if name.startswith('Not') else 'Is'
    return prefix, *map(int, name[len(prefix):].split('_'))


def statement(symbol):
    prefix, r, c, value = decode(symbol)
    return f'Row {r}, column {c} {"cannot be" if prefix == "Not" else "is"} {value}'


def explain(step):
    conclusion, premises = step['conclusion'], step['premises']
    prefix, r, c, value = decode(conclusion)
    if not premises:
        return 'Given', f'{statement(conclusion)}. This number is supplied by the puzzle.'
    if prefix == 'Is':
        removed = ', '.join(str(decode(p)[3]) for p in premises)
        return 'Last candidate', (
            f'Row {r}, column {c} must be {value}: all other values ({removed}) '
            'have been excluded by earlier deductions.'
        )
    _, rr, cc, other = decode(premises[0])
    if (r, c) == (rr, cc):
        why = f'this cell is already {other}, and a cell holds only one number'
        title = 'Cell exclusion'
    elif r == rr:
        why = f'row {r} already has {value} in column {cc}'
        title = 'Row exclusion'
    elif c == cc:
        why = f'column {c} already has {value} in row {rr}'
        title = 'Column exclusion'
    else:
        why = f'its box already has {value} at row {rr}, column {cc}'
        title = 'Box exclusion'
    return title, f'Exclude {value} from row {r}, column {c}, because {why}.'


st.markdown('''
<style>
.block-container {max-width: 1160px; padding-top: 1rem;}
.eyebrow {color: #147d76; font-size: .78rem; font-weight: 700; letter-spacing: .16em;}
.hero {font-size: 2.65rem; font-weight: 750; line-height: 1.12; color: #15333f; margin: 0 0 0.3rem;}
.intro {color: #62747c; max-width: 670px; margin-bottom: 1.8rem;}
.sudoku-board {border-collapse: collapse; table-layout: fixed; width: 100%; max-width: 510px;
 border: 2px solid #274d59; background: white; margin: 0.5rem 0 1rem;}
.sudoku-board td {text-align: center; vertical-align: middle; padding: 0; width: 11.11%;
 height: 50px; border: 1px solid #d7e2e5; font-size: 1.35rem; font-variant-numeric: tabular-nums;}
.sudoku-board .given {color: #173c49; background: #f0f5f6; font-weight: 750;}
.sudoku-board .deduced {color: #008578; font-weight: 500;}
.sudoku-board .box-right {border-right: 2px solid #274d59;}
.sudoku-board .box-bottom {border-bottom: 2px solid #274d59;}
.sudoku-board .selected {background: #fff1bc; box-shadow: inset 0 0 0 2px #d1a837;}
.legend {font-size: .84rem; color: #62747c; margin-bottom: 1rem;}
@media(max-width: 640px) {.hero {font-size: 2rem;} .sudoku-board td {height: 36px; font-size: 1.1rem;}}
</style>
''', unsafe_allow_html=True)

n, box_h, box_w, puzzles = load_puzzles()
st.markdown('<div class="eyebrow">IT5005 · KNOWLEDGE & INFERENCE</div>', unsafe_allow_html=True)
st.markdown('<div class="hero">Sudoku, reason by reason.</div>', unsafe_allow_html=True)
st.markdown('<div class="intro">Solve a puzzle with logic. Then explore the evidence behind a single number, one deduction at a time.</div>', unsafe_allow_html=True)

with st.sidebar:
    st.title('Puzzle desk')
    puzzle_index = st.selectbox(
        'Choose a puzzle', range(len(puzzles)),
        format_func=lambda i: f'Puzzle {i + 1} · {len(puzzles[i])} givens', key='puzzle_index',
    )
    st.caption(f'{n} × {n} grid · {box_h} × {box_w} boxes')
    st.divider()
    st.markdown('**How to explore**')
    st.markdown('1. Select a puzzle.\n2. Choose a solving method.\n3. Ask about a cell.\n4. Follow its proof below.')
    st.caption('Every answer is derived from the givens. No reference answer is used.')

if st.session_state.get('active_puzzle') != puzzle_index:
    st.session_state.active_puzzle = puzzle_index
    st.session_state.pop('solved_result', None)
    st.session_state.pop('query_result', None)
    st.session_state.trace_page = 1

givens = puzzles[puzzle_index]
left, right = st.columns([1.2, 1], gap='large')
board_area = left.container()
with right:
    st.subheader('Solve the whole board')
    algorithm = st.radio('Inference method', ['Forward chaining', 'Backward chaining'], key='algorithm')
    st.caption('Forward starts with the givens. Backward works from candidate values to their supporting facts.')
    if st.button('Solve puzzle', type='primary', use_container_width=True, key='solve'):
        solver = solve_full_grid_fc if algorithm == 'Forward chaining' else solve_full_grid_bc
        with st.spinner(f'Solving with {algorithm.lower()}…'):
            try:
                started = perf_counter()
                solved = solver(n, box_h, box_w, givens)
                elapsed = perf_counter() - started
                st.session_state.solved_result = (solved, elapsed, algorithm)
            except ValueError as error:
                st.error(str(error))
    solved_result = st.session_state.get('solved_result')
    if solved_result:
        st.success(f'Solved with {solved_result[2].lower()} in {solved_result[1]:.3f} s.')
    st.divider()
    st.subheader('Ask about a cell')
    st.caption('Can the rules prove that this cell contains this number?')
    inputs = st.columns(3)
    with inputs[0]:
        row = st.number_input('Row', min_value=1, max_value=n, value=1, step=1, key='row')
    with inputs[1]:
        col = st.number_input('Column', min_value=1, max_value=n, value=1, step=1, key='col')
    with inputs[2]:
        value = st.number_input('Value', min_value=1, max_value=n, value=1, step=1, key='value')
    query_key = (puzzle_index, row, col, value)
    if st.button('Check & explain', use_container_width=True, key='query'):
        with st.spinner('Following the supporting rules…'):
            started = perf_counter()
            kb = build_definite_kb(n, box_h, box_w, givens)
            query = atom('Is', row, col, value)
            verdict = pl_bc_entails(kb, query)
            # The trace helper instruments the very same backward engine.
            target = query if verdict else atom('Not', row, col, value)
            has_proof, trace, rounds = backward_trace(kb, target)
            st.session_state.query_result = {
                'key': query_key, 'verdict': verdict, 'trace': trace,
                'has_proof': has_proof, 'elapsed': perf_counter() - started,
            }
            st.session_state.trace_page = 1
    result = st.session_state.get('query_result')
    if result and result['key'] == query_key:
        if result['verdict']:
            st.success(f'True — row {row}, column {col} is {value}.')
        elif result['has_proof']:
            st.warning(f'False — {value} is excluded from row {row}, column {col}.')
        else:
            st.info('False — the current rules cannot prove this value. This alone does not prove that it is wrong.')
        st.caption(f'Query and proof: {result["elapsed"]:.3f} s')

with board_area:
    st.subheader(f'Puzzle {puzzle_index + 1}')
    metrics = st.columns(3)
    metrics[0].metric('Givens', len(givens))
    metrics[1].metric('To deduce', n * n - len(givens))
    metrics[2].metric('State', 'Solved' if solved_result else 'Ready')
    values = solved_result[0] if solved_result else givens
    st.markdown(board_html(n, box_h, box_w, givens, values, (row, col)), unsafe_allow_html=True)
    st.markdown('<div class="legend">Dark / bold: given &nbsp; · &nbsp; Teal: deduced &nbsp; · &nbsp; Yellow: queried cell</div>', unsafe_allow_html=True)

st.divider()
st.subheader('Follow the proof')
if not result or result['key'] != query_key:
    st.info('Choose a cell and select “Check & explain” to see the rules behind the answer.')
elif not result['has_proof']:
    st.info('No proof was found for this value or its exclusion. More powerful rules may be needed.')
else:
    trace = result['trace']
    if not result['verdict']:
        st.caption('The query was not entailed. The proof below independently establishes why this candidate is excluded.')
    st.caption(f'{len(trace)} supporting steps, ordered so that every premise appears before its conclusion. Shared evidence appears once.')
    page_count = max(1, (len(trace) + 7) // 8)
    page = st.number_input('Proof page', min_value=1, max_value=page_count, step=1, key='trace_page')
    start = (page - 1) * 8
    for i, step in enumerate(trace[start:start + 8], start + 1):
        category, explanation = explain(step)
        with st.expander(f'{i:02d} · {category} — {statement(step["conclusion"])}', expanded=False):
            st.write(explanation)
            if step['premises']:
                st.markdown('**Supporting facts**')
                for premise in step['premises']:
                    st.write('• ' + statement(premise) + '.')
    st.caption(f'Page {page} of {page_count}')
