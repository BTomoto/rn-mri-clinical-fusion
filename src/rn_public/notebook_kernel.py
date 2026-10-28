"""Execute trusted notebook cells with an in-process ipykernel, without ports.

This verifies kernel execution and notebook outputs, not a browser frontend or
a separately running kernel server. In-process execution has no hard timeout.
"""
from pathlib import Path
import asyncio
import io
import os
import queue
import nbformat
from ipykernel.inprocess.manager import InProcessKernelManager
from ipykernel.inprocess.ipkernel import InProcessInteractiveShell


class KernelExecutionError(RuntimeError):
    pass


def execute_notebook(notebook,working_directory):
    """Return the executed notebook. Preserve error output and raise on failure."""
    for cell in notebook.cells:
        if cell.cell_type=='code':cell.outputs=[];cell.execution_count=None
    notebook.metadata['execution_method']='in-process ipykernel via Jupyter client; standard streams captured in memory'
    notebook.metadata['execution_success']=False
    original_cwd=Path.cwd()
    manager=InProcessKernelManager()
    client=None
    original_streams=[]
    iopub_thread=None
    try:
        os.chdir(working_directory)
        # A new manager alone does not clear IPython's singleton display hook.
        # Recreate the shell so rich results cannot target a previous kernel.
        InProcessInteractiveShell.clear_instance()
        manager.start_kernel()
        original_streams=[manager.kernel.stdout,manager.kernel.stderr]
        iopub_thread=manager.kernel.iopub_thread
        manager.kernel.shell.reset(new_session=True)
        client=manager.client()
        client.start_channels()
        for index,cell in enumerate(notebook.cells):
            if cell.cell_type!='code':continue
            outputs=[]
            clear_on_next=[False]
            def append_output(output):
                if clear_on_next[0]:outputs.clear();clear_on_next[0]=False
                if output.output_type=='stream' and outputs and outputs[-1].output_type=='stream' and outputs[-1].name==output.name:
                    outputs[-1].text+=output.text
                else:outputs.append(output)
            def drain():
                while True:
                    try:msg=client.get_iopub_msg(timeout=0)
                    except queue.Empty:break
                    kind=msg['header']['msg_type'];content=msg['content'].copy()
                    if kind in ['stream','display_data','execute_result','error']:
                        content.pop('transient',None)
                        append_output(nbformat.v4.new_output(kind,**content))
                    elif kind=='clear_output':
                        if content.get('wait'):clear_on_next[0]=True
                        else:outputs.clear()
                    elif kind=='update_display_data':
                        raise KernelExecutionError('Updating earlier display IDs is not supported by this audit runner')
            class Capture(io.TextIOBase):
                def __init__(self,name):self.name=name
                def write(self,text):
                    drain()
                    if text:append_output(nbformat.v4.new_output('stream',name=self.name,text=text))
                    return len(text)
                def flush(self):pass
            # In-process OutStream's asynchronous flush is unavailable in this
            # runtime. Capture standard streams in memory; rich results and
            # errors still come from the kernel's Jupyter message queues.
            manager.kernel.stdout=Capture('stdout')
            manager.kernel.stderr=Capture('stderr')
            client.execute(cell.source,store_history=True,allow_stdin=False,stop_on_error=True)
            drain()
            reply=client.get_shell_msg(timeout=5)['content']
            cell.execution_count=reply.get('execution_count')
            cell.outputs=outputs
            if reply.get('status')!='ok':
                raise KernelExecutionError(f'Cell {index+1}: {reply.get("ename","error")}: {reply.get("evalue","")}')
        notebook.metadata['execution_transport']='in_process_no_network_or_filesystem_sockets'
        notebook.metadata['execution_success']=True
        nbformat.validate(notebook)
        return notebook
    finally:
        if client is not None:client.stop_channels()
        for stream in original_streams:stream.close()
        if iopub_thread is not None and iopub_thread.thread.is_alive():
            # ipykernel 7.4's stop() stops its dedicated loop before cancelled
            # housekeeping tasks get an event-loop turn. Await them first.
            async def finish_tasks():
                tasks=[t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
                for task in tasks:task.cancel()
                await asyncio.gather(*tasks,return_exceptions=True)
            asyncio.run_coroutine_threadsafe(finish_tasks(),iopub_thread.io_loop.asyncio_loop).result(timeout=5)
        if manager.has_kernel:manager.shutdown_kernel()
        InProcessInteractiveShell.clear_instance()
        os.chdir(original_cwd)
