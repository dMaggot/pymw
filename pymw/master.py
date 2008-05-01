#!/usr/bin/env python

from pymw import *
import pymw.interfaces.mpi_interface
from time import *

interface = pymw.interfaces.mpi_interface.MPIInterface(num_workers=4)
pymw_master = pymw.pymw.PyMW_Master(interface=interface)

total = 0
start = time()
tasks = [pymw_master.submit_task('worker.py', input_data=i) for i in range(10)]
for task in tasks:
	task, res = pymw_master.get_result(task)
	total = total + res
end = time()

print "The answer is", total
print "Total time:", str(end-start)

