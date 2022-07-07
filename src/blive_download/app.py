from threading import Thread
import time,datetime
import os
import sys
import signal

from .storage import StorageManager
from .recorder import Recorder

from .model import clear_status, connect_db, RecorderManager
from ..utils import configCheck
from ..utils import Myproc
        
# from blive_upload import upload
#This absolute path import requires root directory have "blive_upload" folder

LOG_PATH = "logs"

class App():
    def __init__(self, upload_func, configpath):
        self.upload_func = upload_func
        self.configpath = configpath
        
        self.time_create = datetime.datetime.now()
        self.recorders = {}
        self.engine = None

        self.conf = configCheck(configpath)
        self.database = self.conf["_default"].get("Database")
        self.engine = connect_db(self.database)

        self.storage_manager = StorageManager(self.conf["_default"]["_path"], self.engine)
        self.recorder_manager = RecorderManager(engine = self.engine)

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

        if self.conf["_default"]["Enabled_recorder"]:
            recorder_enabled = self.conf["_default"]["Enabled_recorder"]
        else:
            recorder_enabled = self.conf.keys()

        t = Thread(target = self.storage_manager.loop)
        t.daemon = True
        t.start()

        try:
            for up_name in self.conf.keys():
                if up_name == "_default" or up_name not in recorder_enabled:
                    continue
                self.recorder_manager.add_task(up_name)

            while True:
                should_run_set = set([i.nickname for i in self.recorder_manager.get_task() if i.should_running == True])
                for up_name in should_run_set - self.recorders.keys():
                    p = self.prep_record_Process(up_name)            
                    self.run_record_Process(up_name, p)
                    
                    print("[%s]Recorder loaded"%up_name,datetime.datetime.now(), flush=True)
                    time.sleep(0.1)
                    # print("[%s]Recorder set"%up_name,datetime.datetime.now(), flush=True)
                for up_name in self.recorders.keys() - should_run_set:
                    # print(self.recorders[up_name].pid)
                    os.kill(self.recorders[up_name].pid, signal.SIGINT) 
                    self.recorders[up_name].join()

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
                    self.recorder_manager.update_pid(up_name, 0)

                    self.recorder_manager.kill_task(up_name)   #Avoid keep restarting the dead process. 

                time.sleep(30)
        finally:
            for up_name, p in self.recorders.items():
                os.kill(p.pid, signal.SIGINT)
            clear_status(self.engine)
            
            print("Exit Successfully!")

    def handle_stopped(self, up_name):
        self.recorders.pop(up_name)

    def prep_record_Process(self, up_name) :
        p = Myproc(target = self.run_recorder, args=(up_name, self.configpath, self.upload_func), name = "[{}]Recorder".format(up_name))
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
        self.recorder_manager.update_pid(up_name, p.pid)
        return

    @staticmethod
    def run_recorder(up_name, configpath, upload_func):
        recorder = Recorder(up_name)
        recorder.init_from_json(configpath, upload_func)
        recorder.run()
