from concurrent.futures import ThreadPoolExecutor
import datetime
import logging
import os
import sys
import time
# import subprocess
from typing import Any, Callable, List, Optional, Tuple

from ..blive_upload.cfg_upload import configured_upload


from ..utils import Myproc, configCheck
from .api import get_stream_url, is_live, get_room_id, get_room_info
from .videohandler import burn_subtitle, flvmeta, record_ffmpeg, record_source
from ..model import Video_DB, connect_db, Live
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
        "flvtag_update",    #Is this needed?
        "upload_flag",      #Is this needed?
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
    upload_configuration: Optional[str]
    upload_func: Callable

    live_dir: str
    live_status: bool
    live : Live
    engine : Any
    ws_manage: WebSocketAppManager
    
    record_check: Callable[[int, float], int]
    record: Callable

    def __init__(self, up_name:str) -> None:
        self.up_name = up_name
        self.callback_list:List[Callable[[Video_DB],None]]
        # self.callback_list = [
        #     flvmeta,
        #     self.dump_video_json
        # ]
        # self.record = record_source

        self.callback_list = [burn_subtitle]
        self.record = record_source     #Think about how to pass this

        self.upload_func = configured_upload
        
    def init_from_json(self, config_file:str):
        '''
        Set recorder as configured. UP specified configuration will overwrite the global setting. 
        '''
        default_conf = configCheck(configpath= config_file)
        #Set default settings
        for key in Recorder.REQUIRED_KEY:
            if key in default_conf:
                setattr(self, key, default_conf[key])
        
        self.database = default_conf.get("Database")
        self.upload_configuration = default_conf.get("Upload_configuration")    
        conf = configCheck(configpath= config_file, up_name = self.up_name)
        
        #Set UP specified settings
        for key in Recorder.REQUIRED_KEY:
            if key in conf:
                setattr(self, key, conf[key])

        print(f"Record from live room {self.room_id}")
        print(f"Split videos by {self.divide_video}")
        if self.upload_flag == 1:
            print("自动上传已启用")
            if not self.upload_configuration:
                print("upload_configuration not provided")
        else:
            print("自动上传未启用")
        
        print("Flvmeta Mode:", self.flvtag_update)
        print("Storage Mode:", self.storage_stg)
        
        print("[%s]Recorder loaded"%self.up_name,datetime.datetime.now(), flush=True)
        sys.stdout.flush()

    def check(self):
        '''
        Check if all necessary components(REQUIRED_KEY) are set, and preset all relavant components
        '''
        for key in Recorder.REQUIRED_KEY:
            if not hasattr(self, key):
                raise Exception(f"Attribute {key} is not properly set")
        
        self.live_status = False
        self.room_id = get_room_id(self.room_id)
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
            self.engine = connect_db(self.database["link"]) #type:ignore
            print(f"Connected to {self.database} database")
        else:
            self.engine = None
            print("No database provided, operate in offline mode")


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
        self.live = Live(online = bool(self.engine), engine = self.engine)
        live_title = get_room_info(self.room_id).get("title","")
        self.live.from_new(self.up_name,self.room_id, self.live_dir, live_title = live_title)

        
        self.ws_manage = WebSocketAppManager(self.room_id)
        self.ws_manage.handler = generate_handler(self.live)
        self.ws_manage.run_ws_recon_thread()
        self.post_record_executor = ThreadPoolExecutor(max_workers=1)

        self.live.set_json()
        self.live.dump_json()
    def __new_live_finalize(self, fail = False):
        if self.live.live_db.end_time is None:
            if self.live.curr_video and not self.live.curr_video.end_time: #Change this in the future 修改 del curr_video after finalize
                curr_videoanme = self.live.curr_video.videoname
                self.live.finalize_video(
                    True, 
                    int(time.time()), 
                    0 if not os.path.isfile(curr_videoanme) else os.path.getsize(curr_videoanme), 
                    self.storage_stg,
                    self.live.curr_video
                    )

            self.live.from_new_finalize(int(time.time())) 
        if not fail:
            self.post_record_executor.shutdown(wait=True)
  
        self.ws_manage.maintain_ws = False
        self.live.set_json()
        self.live.dump_json()
        print("Live Done ",datetime.datetime.now(), flush = True)

        del self.live

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

    def __init_new_video(self) -> Video_DB:
        '''
        Generate the file name for the new video, as well as other initilization for the new video piece.
        '''
        #New video starts, using a temp filename
        curr_video = self.live.init_video()

        live_title = get_room_info(self.room_id).get("title", "")
        curr_video.live_title = live_title  #type:ignore
        
        return curr_video

    def __finalize_new_video(self, video: Video_DB, rtncode, video_size):

        def finalize_wrapper(is_stored: bool, end_time: int, size: int, storage_stg: int) -> Callable[[Video_DB],None]:
            def _(video: Video_DB)->None:
                self.live.finalize_video(is_stored, end_time, size, storage_stg, video = video)
            return _
        
        def post_record(video_db:Video_DB, callback_list: List[Callable[[Video_DB],None]]):
            for callback in callback_list:
                try:
                    callback(video_db)
                except Exception as e:
                    logging.exception(e)

        if not rtncode:
            #Modify recorded video and dump updated record_info
            callback_list = self.callback_list + [finalize_wrapper(True, int(time.time()), video_size, self.storage_stg), self.dump_video_json]
            self.post_record_executor.submit(
                post_record,
                video,
                callback_list
                )
            # t_post_record = Thread(
            #     target=self.__post_record, 
            #     args=(video,self.callback_list + [finalize_wrapper(True, int(time.time()), video_size, self.storage_stg), self.dump_video_json]), 
            #     name=video.videoname
            #     ) 
            # t_post_record.start()
            # self.threads.append(t_post_record)
        else:
            print("record failed on {}".format(video.videoname))
            self.live.finalize_video(False, int(time.time()), 0, self.storage_stg, video = video)

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
                video = self.__init_new_video()
                
                self.live.curr_video = video
                rtncode, video_size = self.record(real_url, video.videoname, self.record_check) 
                self.live.curr_video = None
                
                self.__finalize_new_video(video, rtncode,video_size)
                time.sleep(1)
            self.__new_live_finalize()

    def __upload(self):
        if self.live.json_file is None:
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
            p = Myproc(target = self.upload_func, args = (self.live.json_file,self.upload_configuration), name="[{}]Uploader".format(self.up_name))
            p.set_output_err(logfile)
            p.start()
            p.post_run()
            print("=============================")
            print("开始上传"+ self.live.json_file)
            print("=============================")

    def dump_video_json(self,video_db: Video_DB):
        self.live.json_append_video(video_db)
        self.live.dump_json()

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

