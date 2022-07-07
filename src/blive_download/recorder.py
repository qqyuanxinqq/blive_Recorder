import datetime
import logging
import os
import sys
import time
from threading import Thread
# import subprocess
from typing import Any, Callable, List, Optional, Tuple


from ..utils import Myproc, configCheck
from .api import get_stream_url, is_live, record_ffmpeg, record_source, room_id
from .flvmeta import flvmeta_update
from .model import Video_DB, connect_db, Live
from .ws import Message_Handler, WebSocketAppManager, generate_handler



class Recorder():
    '''
    Init by config file By_config(upname:str)
    Init by construction, mannually, support by silence()
    For given Recorder setting, By_input(upname:str, live_dir:str, room_id)

    How to set a recorder and reuse it for different rooms?
        Custom on instance seems not working

    '''

    REQUIRED_KEY = [
        "room_id",
        "divide_video",
        "flvtag_update",
        "upload_flag", 
        "path",
        "storage_stg",
    ]

    room_id: int
    divide_video: Tuple[str,float]
    upload_flag: int
    flvtag_update: int
    path: str
    storage_stg: int

    database: Optional[str] 
    upload_func: Optional[Callable]

    live_dir: str
    live_status: bool
    live : Live
    engine : Any
    ws_manage: WebSocketAppManager
    
    record_check: Callable[[int, float], int]
    record: Callable

    def __init__(self, up_name:str) -> None:
        self.up_name = up_name
        self.callback_list:List[Callable[[Video_DB],None]] = [
            flvmeta,
            self.dump_video_json
        ]
        self.threads = []

    def init_from_json(self, config_file:str , upload_func =None):
        self.upload_func = upload_func   #Think about how to pass this

        self.record = record_source     #Think about how to pass this
                
        default_conf = configCheck(configpath= config_file)
        self.room_id = default_conf["room_id"]
        self.divide_video = default_conf["divide_video"]
        self.flvtag_update = default_conf["flvtag_update"]
        self.upload_flag = default_conf["upload_flag"]
        self.path = default_conf["path"]
        self.storage_stg = default_conf["storage_stg"]
        
        self.database = default_conf.get("Database")  
        conf = configCheck(configpath= config_file, up_name = self.up_name)
        
        for key in Recorder.REQUIRED_KEY:
            if key in conf:
                setattr(self, key, conf[key])

        print(f"Record from live room {self.room_id}")
        print(f"Split videos by {self.divide_video}")
        if self.upload_flag == 1:
            print("自动上传已启用")
        else:
            print("自动上传未启用")
        
        print("Flvmeta Mode:", self.flvtag_update)
        print("Storage Mode:", self.storage_stg)
        
        print("[%s]Recorder loaded"%self.up_name,datetime.datetime.now(), flush=True)
        sys.stdout.flush()

    def check(self):
        '''
        Check if all necessary components are set, and preset all relavant components
        '''
        for key in Recorder.REQUIRED_KEY:
            if not hasattr(self, key):
                raise Exception(f"Attribute {key} is not properly set")
        
        self.live_status = False
        self.room_id = room_id(self.room_id)
        self.live_dir = os.path.join(self.path, self.up_name)
        os.makedirs(self.live_dir, exist_ok = True)

        if self.divide_video[0] == 'size':
            self.record_check = check_size(self.divide_video[1])
        elif self.divide_video[0] == 'duration':
            self.record_check = check_duration(self.divide_video[1])
        elif self.divide_video[0] == 'rounding':
            self.record_check = check_rounding_time(self.divide_video[1])
        else:
            raise AttributeError("_divide_video entry not properly set!!!")

        if self.database:
            self.engine = connect_db(self.database) #type:ignore
            print(f"Connected to {self.database} database")
        else:
            self.engine = None
            print("No database provided")

    def run(self):
        os.environ['TZ'] = 'Asia/Shanghai'
        if os.name != 'nt':
            time.tzset()
        self.check()
        try:
            self.recording()
        except Exception as e:
            logging.exception(e)
        finally:
            if hasattr(self,"live"):
                # self.__post_record
                self.__new_live_finalize(fail = True)
            print("[%s]Recorder Terminated Gracefully!"%self.up_name)

    def __new_live_init(self) -> None:
        self.live = Live(online = bool(self.database), engine = self.engine)
        self.live.from_new(self.up_name,self.room_id, self.live_dir)     
        
        self.ws_manage = WebSocketAppManager(self.room_id)
        self.ws_manage.handler = generate_handler(self.live)
        self.ws_manage.run_ws_recon_thread()

        self.live.set_record_info()
        self.live.dump_json()
        self.threads = []
    def __new_live_finalize(self, fail = False):
        if not fail:
            self.live.from_new_finalize(int(time.time())) 
            while self.threads:
                self.threads.pop().join()
            time.sleep(10)
  
        self.ws_manage.maintain_ws = False
        self.live.json_live_end()
        self.live.dump_json()
        print("Live Done ",datetime.datetime.now(), flush = True)

    def __check_live_status(self):
        try:
            self.live_status = is_live(self.room_id)
        except Exception as e:
            logging.exception(e)

        return self.live_status

    def __get_stream_url(self):
        try:
            real_url = get_stream_url(self.room_id)
        except Exception as e:
            logging.exception(e)
            return None
        return real_url

    def __init_new_video(self) -> str:
        '''
        Generate the file name for the new video, as well as other initilization for the new video piece.
        '''
        #New video starts
        self.live.init_video()
        assert self.live.curr_video

        return self.live.curr_video.videoname

    def __finalize_new_video(self, rtncode,video_size):
        assert self.live.curr_video
        if not rtncode:
            #Modify recorded video and dump updated record_info
            self.live.finalize_video(True, int(time.time()), video_size, self.storage_stg)
            
            t_post_record = Thread(target=self.__post_record, args=(self.live.curr_video,), name=self.live.curr_video.videoname) 
            t_post_record.start()
            self.threads.append(t_post_record)
        else:
            print("record failed on {}".format(self.live.curr_video.videoname))
            self.live.finalize_video(False, int(time.time()), 0, self.storage_stg)
        
    def __post_record(self, video_db:Video_DB):
        for callback in self.callback_list:
            callback(video_db)

    def recording(self):
        while True:
            while not self.__check_live_status():
                print("[%s]未开播"%self.room_id,datetime.datetime.now(), flush=True)
                time.sleep(35)

            self.__new_live_init()
            
            #Init upload process  
            if self.upload_flag == 1:
                self.__upload()
        
            #Record this live
            while self.__check_live_status() == True:                   
                real_url = self.__get_stream_url()
                if real_url == None:
                    print("开播了但是没有源")
                    time.sleep(5)
                    continue
                video_file = self.__init_new_video()
                rtncode, video_size = self.record(real_url, video_file, self.record_check) 
                self.__finalize_new_video(rtncode,video_size)
            self.__new_live_finalize()

    def __upload(self):
        if not self.upload_func:
            print("=============================")
            print("No upload function provided")
            print("=============================")
        elif self.live.json_file is None:
            print("=============================")
            print("self.live.json_file provided as None")
            print("=============================")
        else:
            upload_log_dir = os.path.join(self.live_dir,"upload_log")
            os.makedirs(upload_log_dir, exist_ok = True)
            logfile = os.path.join(
                upload_log_dir, 
                self.live.live_db.time_create.strftime(self.live.TIMEFORMAT) + '.log'
                )
            #Uploading process runs at blive_upload directory
            # p = subprocess.Popen(['nohup python3 -u ./blive_upload/{}.py {} > {} 2>&1  & echo $! > {}'.format(\
            # self.up_name,record_info.get('filename'), logfile, logfile)],\
            # shell=True)
            p = Myproc(target = self.upload_func, args = (self.live.json_file,), name="[{}]Uploader".format(self.up_name))
            p.set_output(logfile)
            p.start()
            p.post_run()
            print("=============================")
            print("开始上传"+ self.live.json_file)
            print("=============================")

    def dump_video_json(self,video_db: Video_DB):
        self.live.json_append_video(video_db)
        self.live.dump_json()


def flvmeta(video_db:Video_DB):
    filename = video_db.videoname
    print("==========Flvmeta============\n", filename, flush = True)
    rtn = flvmeta_update(filename)
    print("==========Flvmeta============\n", rtn, flush = True)


def check_size(size_limit):
    '''
    Return a function that returns True if video size exceeds size_limit(Gb)
    '''
    def check_func(size, duration):
        del duration
        return True if size >= size_limit*1024*1024*1024 else False
    return check_func
def check_duration(duration_limit):
    '''
    Retrun a function that returns True if the video duraction(seconds) exceeds duration_limit.
    The duraction measure is not accurate, because it relies on how long the recording function runs. 
    '''
    def check_func(size, duration):
        del size
        return True if duration >= duration_limit else False
    return check_func

def check_rounding_time(rounding):
    '''
    Retrun a function that returns True if the time approches the whole number of the rounding.
    '''
    minimum = 5
    def check_func(size, duration):
        del size
        if time.time()%rounding <=minimum and duration >= minimum:
            return True
        else:
            return False
    return check_func

