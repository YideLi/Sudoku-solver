import unittest
from streamlit.testing.v1 import AppTest


class AppTests(unittest.TestCase):
    def test_solve_query_pagination_and_puzzle_switch(self):
        app = AppTest.from_file('sudoku_app.py', default_timeout=120).run()
        self.assertFalse(app.exception)
        app.button(key='solve').click().run()
        self.assertIn('forward chaining', app.success[0].value)
        app.button(key='query').click().run()
        self.assertTrue(any('True' in item.value for item in app.success))
        self.assertEqual(len(app.expander), 8)
        app.number_input(key='trace_page').set_value(2).run()
        self.assertIn('09', app.expander[0].label)
        app.number_input(key='value').set_value(2).run()
        self.assertEqual(len(app.expander), 0)  # stale evidence disappears
        app.button(key='query').click().run()
        self.assertIn('False', app.warning[0].value)
        self.assertEqual(app.number_input(key='trace_page').value, 1)
        app.selectbox(key='puzzle_index').set_value(4).run()
        self.assertEqual(len(app.success), 0)
        self.assertEqual(len(app.expander), 0)
        app.radio(key='algorithm').set_value('Backward chaining').run()
        app.button(key='solve').click().run()
        self.assertIn('backward chaining', app.success[0].value)
        self.assertFalse(app.exception)


if __name__ == '__main__':
    unittest.main()
