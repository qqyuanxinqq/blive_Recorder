import time,datetime
import os
import sys
import signal
# import subprocess

from .recorder import Recorder

from .table import add_task, clear_status, create_db, get_task, kill_task, update_pid
from .utils import configCheck
from .utils import Myproc
        
# from blive_upload import upload
#This absolute path import requires root directory have "blive_upload" folder


LOG_PATH = "logs"


class App():
    def __init__(self, upload_func):
        self.upload_func = upload_func
        
        self.time_create = datetime.datetime.now()
        self.recorders = {}
        self.engine = None

        conf = configCheck()
        self.database = conf["_default"].get("Database")

        os.makedirs(LOG_PATH, exist_ok = True)


    def run(self):
 
        '''
        should_running >= self.recorders >= Processes
        First, add tasks into the db
        while True:
            Check_task = (db_set - python_set), and start_p
            Check_task = (python_set - db_set), and kill_p
            
            check p in python_set:
                if dead: 
                    remove from python_set
                    remove from db_set
                    kill task                    
            
        '''       
        if self.database:
            self.engine = create_db(self.database)
        else:
            raise Exception("Please provide valid database directory!!!")

        conf = configCheck()
        if conf["_default"]["Enabled_recorder"]:
            recorder_enabled = conf["_default"]["Enabled_recorder"]
        else:
            recorder_enabled = conf.keys()
        
        
        try:
            for up_name in conf.keys():
                if up_name == "_default" or up_name not in recorder_enabled:
                    continue
                add_task(self.engine, up_name)

            while True:
                should_run_set = set([i.nickname for i in get_task(self.engine) if i.should_running == True])
                for up_name in should_run_set - self.recorders.keys():
                    p = self.prep_record_Process(up_name)            
                    self.run_record_Process(up_name, p)
                    
                    print("[%s]Recorder loaded"%up_name,datetime.datetime.now(), flush=True)
                    time.sleep(0.1)
                    # print("[%s]Recorder set"%up_name,datetime.datetime.now(), flush=True)
                for up_name in self.recorders.keys() - should_run_set:
                    os.kill(self.recorders[up_name].pid, signal.SIGINT) 

                stopped = []
                for up_name, p in self.recorders.items():
                    if not p.is_alive():
                        print(datetime.datetime.now(),":")
                        print("{} has stopped!".format(p.name))
                        sys.stdout.flush()
                        stopped.append(up_name)
                while stopped:
                    up_name = stopped.pop()
                    self.recorders[up_name].close()

                    self.recorders.pop(up_name)
                    update_pid(self.engine, up_name, 0)

                    kill_task(self.engine, up_name)   #Avoid keep restarting the dead process. 

                time.sleep(30)
        finally:
            for up_name, p in self.recorders.items():
                os.kill(p.pid, signal.SIGINT)
            clear_status(self.engine)
            print("Exit Successfully!")


    
    def handle_stopped(self, up_name):
        self.recorders.pop(up_name)

    def prep_record_Process(self, up_name) :
        p = Myproc(target = self.run_recorder, args=(up_name, self.upload_func), name = "[{}]Recorder".format(up_name))
        logfile = os.path.join(LOG_PATH, up_name + self.time_create.strftime("_%Y%m%d_%H-%M-%S") + '.log')
        p.set_output(logfile)
        return p
    def run_record_Process(self,up_name, p):
        '''
        '''
        self.recorders[up_name] = p
        p.start()
        p.post_run()

        if not p.pid:
            print("[{}] Missing PID!!!!!!!!".format(up_name))
        update_pid(self.engine, up_name, p.pid)
        return

    @staticmethod
    def run_recorder(up_name, upload_func):
        recorder = Recorder(up_name, upload_func)
        recorder.recording()
