from app_types import *
from pymw import *
from base_interface import *
import time

base_interface = BaseSystemInterface(num_workers=4)
pymw_master = PyMW_Master(interface=base_interface)

total = 0

start = time.time()
tasks = [pymw_master.submit_task('worker.py', Input(i)) for i in range(10)]
for task in tasks:
	total += pymw_master.get_result(task).value
end = time.time()

print "The answer is", total
print "Total time:", str(end-start)

print pymw_master.get_status()

pymw_master.cleanup()
