import os
import time,datetime
import sys
from multiprocessing import get_context
from threading import Thread
import logging

#Todo??? Provide a registeration decorator, so the App manager can easiliy get the process list
class Myproc(get_context('spawn').Process):
    def __init__(self, group=None, target=None, name=None, args=(), kwargs={},
                 *, daemon=None):
        """
        Overwritten Process class with stdout, stderr redirection.
        """

        super().__init__(group, target, name, args, kwargs, daemon=daemon)  # type: ignore
        self.logfile = ""
        self.path = "."  

    def run(self):
        time.sleep(0.1)
        print("===========Myproc==========")
        print(datetime.datetime.now())
        print("Process ", self.name, "has started.")
        print("Process spawned at PID: ",os.getpid())
        print("===========================",flush=True)
        time.sleep(0.1)
        with open(self.logfile, "w") as f:
            sys.stdout = f
            sys.stderr = f
            print("PID: ", os.getpid(),flush=True)
            if self._target:  # type: ignore
                try:
                    self._target(*self._args, **self._kwargs)  # type: ignore
                except Exception as e:
                    logging.exception(e)

    def _post_run(self):
        self.join()
        print("===========Myproc==========")
        print(datetime.datetime.now())
        print("Process ", self.name, "has terminated, exit code: ", self.exitcode)
    
    def post_run(self):
        t = Thread(target = self._post_run)
        t.start()
        
    def set_output_err(self,logfile):
        self.logfile = logfile

    def set_path(self,path):
        self.path = path