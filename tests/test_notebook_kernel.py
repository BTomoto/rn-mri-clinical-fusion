from pathlib import Path
import sys
import tempfile
import unittest
import nbformat

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from rn_public.notebook_kernel import execute_notebook,KernelExecutionError


class NotebookKernelTests(unittest.TestCase):
    def test_kernel_keeps_state_and_captures_streams_and_results(self):
        nb=nbformat.v4.new_notebook(cells=[nbformat.v4.new_code_cell('x = 21'),
            nbformat.v4.new_code_cell("import sys\nprint('stdout')\nprint('stderr',file=sys.stderr)\nx*2")])
        with tempfile.TemporaryDirectory() as p:execute_notebook(nb,Path(p))
        out=nb.cells[1].outputs
        self.assertEqual([x.output_type for x in out],['stream','stream','execute_result'])
        self.assertEqual(out[0].name,'stdout');self.assertEqual(out[0].text,'stdout\n')
        self.assertEqual(out[1].name,'stderr');self.assertEqual(out[1].text,'stderr\n')
        self.assertEqual(out[2].data['text/plain'],'42')
        nbformat.validate(nb)

    def test_cell_error_is_not_reported_as_success(self):
        nb=nbformat.v4.new_notebook(cells=[nbformat.v4.new_code_cell("raise ValueError('intentional fixture')")])
        with tempfile.TemporaryDirectory() as p:
            with self.assertRaises(KernelExecutionError):execute_notebook(nb,Path(p))
        self.assertTrue(any(o.output_type=='error' and o.ename=='ValueError' for o in nb.cells[0].outputs))

    def test_fresh_kernel_does_not_reuse_prior_notebook_variables(self):
        a=nbformat.v4.new_notebook(cells=[nbformat.v4.new_code_cell('private_fixture_variable=9')])
        b=nbformat.v4.new_notebook(cells=[nbformat.v4.new_code_cell("'private_fixture_variable' in globals()")])
        with tempfile.TemporaryDirectory() as p:
            execute_notebook(a,Path(p));execute_notebook(b,Path(p))
        self.assertEqual(b.cells[0].outputs[-1].data['text/plain'],'False')

    def test_failure_clears_stale_outputs_of_unexecuted_cells(self):
        stale=nbformat.v4.new_code_cell("print('not reached')",execution_count=99,
            outputs=[nbformat.v4.new_output('stream',name='stdout',text='old success')])
        nb=nbformat.v4.new_notebook(cells=[nbformat.v4.new_code_cell("raise ValueError('fixture')"),stale])
        with tempfile.TemporaryDirectory() as p:
            with self.assertRaises(KernelExecutionError):execute_notebook(nb,Path(p))
        self.assertEqual(nb.cells[1].outputs,[])
        self.assertIsNone(nb.cells[1].execution_count)
        self.assertFalse(nb.metadata.execution_success)
