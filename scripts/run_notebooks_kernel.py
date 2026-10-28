"""Run chosen notebooks in an in-process Jupyter kernel; default is Notebook 05."""
from pathlib import Path
import argparse
import datetime as dt
import hashlib
import importlib.metadata
import json
import sys
import nbformat

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from rn_public.notebook_kernel import execute_notebook


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('notebooks',nargs='*')
    parser.add_argument('--report',default='reports/kernel_execution.json',help='Execution receipt path relative to project root')
    args=parser.parse_args()
    paths=[ROOT/p for p in args.notebooks] if args.notebooks else [ROOT/'notebooks/05_endpoint_versions_and_followup.ipynb']
    records=[]
    report=ROOT/args.report
    report.parent.mkdir(parents=True,exist_ok=True)
    status=dict(mode='in_process_ipykernel',separate_kernel_server_tested=False,browser_frontend_tested=False,
        versions={p:importlib.metadata.version(p) for p in ['ipykernel','IPython','nbformat','jupyter-client']},
        notebooks=records,success=False)
    try:
        for path in paths:
            nb=nbformat.read(path,as_version=4)
            source_hash=hashlib.sha256('\n'.join(c.source for c in nb.cells if c.cell_type=='code').encode()).hexdigest()
            try:
                execute_notebook(nb,ROOT)
            except Exception:
                nbformat.write(nb,path)
                records.append(dict(path=str(path.relative_to(ROOT)),success=False,code_sha256=source_hash))
                raise
            nbformat.write(nb,path)
            records.append(dict(path=str(path.relative_to(ROOT)),code_cells=sum(c.cell_type=='code' for c in nb.cells),
                code_sha256=source_hash,errors=sum(o.output_type=='error' for c in nb.cells if c.cell_type=='code' for o in c.outputs)))
            print('Kernel-executed',path.name,flush=True)
        status['success']=True
    except Exception as exc:
        status['error']=f'{type(exc).__name__}: {exc}'
        raise
    finally:
        status['checked_at_utc']=dt.datetime.now(dt.timezone.utc).isoformat()
        report.write_text(json.dumps(status,indent=2))


if __name__=='__main__':main()
