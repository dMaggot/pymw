#!/usr/bin/env python
"""Provide a multicore interface for master worker computing with PyMW.
"""

__author__ = "Eric Heien <e-heien@ist.osaka-u.ac.jp>"
__date__ = "22 February 2009"

import subprocess
import sys
import ctypes
import os
import signal
import errno
import cPickle
import cStringIO

"""On worker restarting:
Multicore systems cannot handle worker restarts - recording PIDs
can result in unspecified behavior (especially if the system is restarted).
The solution is to check for a result on program restart - if it's not there,
delete the directory and start the task anew."""

class Worker:
    def __init__(self):
        self._exec_process = None
    
    def _kill(self):
        try:
            if self._exec_process:
                if sys.platform.startswith("win"):
                    ctypes.windll.kernel32.TerminateProcess(int(self._exec_process._handle), -1)
                else:
                    os.kill(self._exec_process.pid, signal.SIGKILL)
        except:
            pass

class MulticoreInterface:
    """Provides a simple interface for single machine systems.
    This can take advantage of multicore by starting multiple processes."""

    def __init__(self, num_workers=1, python_loc="python"):
        self._num_workers = num_workers
        self._available_worker_list = []
        self._worker_list = []
        self._python_loc = python_loc
        self._input_objs = {}
        self._output_objs = {}
        self.pymw_interface_modules = "cPickle", "sys", "cStringIO"
        for worker_num in range(num_workers):
            w = Worker()
            self._available_worker_list.append(w)
            self._worker_list.append(w)
    
    def get_available_workers(self):
        return list(self._available_worker_list)
    
    def reserve_worker(self, worker):
        self._available_worker_list.remove(worker)
    
    def worker_finished(self, worker):
        self._available_worker_list.append(worker)
    
    def execute_task(self, task, worker):
        if sys.platform.startswith("win"): cf=0x08000000
        else: cf=0
        
        # Pickle the input argument and remove it from the list
        input_obj_str = cPickle.dumps(self._input_objs[task._input_arg])

        worker._exec_process = subprocess.Popen(args=[self._python_loc, task._executable, task._input_arg, task._output_arg],
                                                creationflags=cf, stdin=subprocess.PIPE,
                                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        # Wait for the process to finish
        proc_stdout, proc_stderr = worker._exec_process.communicate(input_obj_str)
        retcode = worker._exec_process.returncode
        if retcode is 0:
            self._output_objs[task._output_arg] = cPickle.loads(proc_stdout)
            if task._file_input==True:
                self._output_objs[task._output_arg][0]=[task._output_arg]
        else:
            raise Exception("Executable failed with error "+str(retcode), proc_stderr)
                
        worker._exec_process = None
        task.task_finished()    # notify the task

    def _cleanup(self):
        for worker in self._worker_list:
            worker._kill()
    
    def get_status(self):
        return {"num_total_workers" : self._num_workers,
            "num_active_workers": self._num_workers-len(self._available_worker_list)}
    
    def pymw_master_read(self, loc):
        return self._output_objs[loc]
    
    def pymw_master_write(self, output, loc):
    	self._input_objs[loc] = output
    
    def pymw_worker_read(options):
        return cPickle.Unpickler(sys.stdin).load()
    
    def pymw_worker_write(output, options):
        if "file_input" in options:
            outfile = open(sys.argv[2], 'w')
            cPickle.Pickler(outfile).dump(output[0])
            outfile.close()
            output[0]=None
        print cPickle.dumps(output)

    def pymw_worker_func(func_name_to_call, options):
        # Get the input data
        input_data = pymw_worker_read(options)
        if not input_data: input_data = ()
        # Execute the worker function
        if "file_input" in options:
            filedata=[]
            try:
                for i in input_data[0]:
                    f=open(i,"r")
                    filedata+=cPickle.loads(f.read())
            except:
                for i in input_data[0]:
                    f=open(i[0],"r")
                    f.seek(i[1])
                    filedata.append(f.read(i[2]-i[1]))
            result = func_name_to_call(filedata)
        else:
            result = func_name_to_call(*input_data)
        pymw_emit_result(result)
