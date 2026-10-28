"""Execute pure-Python notebook cells in order, recording standard nbformat outputs.

This lightweight runner does not need IPython. The same notebooks can be opened
and rerun in JupyterLab. Shell magics and rich display hooks are intentionally absent.
"""
import contextlib
import io
import json
import os
from pathlib import Path
import traceback

root = Path(__file__).resolve().parents[1]
os.chdir(root)
for path in sorted((root / 'notebooks').glob('*.ipynb')):
    notebook = json.loads(path.read_text())
    namespace = {'__name__': '__main__'}
    number = 0
    for cell in notebook['cells']:
        if cell['cell_type'] != 'code':
            continue
        number += 1
        cell['execution_count'] = number
        stdout = io.StringIO()
        try:
            with contextlib.redirect_stdout(stdout):
                exec(compile(''.join(cell['source']), f"{path.name}:cell{number}", 'exec'), namespace)
        except Exception as exc:
            cell['outputs'] = [{'output_type':'error','ename':type(exc).__name__, 'evalue':str(exc),'traceback':traceback.format_exc().splitlines()}]
            path.write_text(json.dumps(notebook, ensure_ascii=False, indent=1))
            raise
        cell['outputs'] = [{'output_type':'stream','name':'stdout','text':stdout.getvalue().splitlines(True)}]
    notebook['metadata']['execution_method'] = 'scripts/run_notebooks.py; ordinary Python cells, compatible with JupyterLab'
    path.write_text(json.dumps(notebook, ensure_ascii=False, indent=1))
    print('Executed', path.name, 'cells:', number)
