import datetime, time
import os
import json
from typing import Optional

from filelock import FileLock
from sqlalchemy.orm import Session

from .db import Live_DB, TableManager, Video_DB
from ...utils import Retry

@Retry(max_retry = 5, interval = 10).decorator
class LiveManager(TableManager):
    def add_live(self, live: Live_DB):
        with Session(self.engine) as session:
            session.expire_on_commit = False
            session.add(live)
            session.commit()
            temp = live.videos  #Actively access its children to eager load
        return live

    

class Live():
    '''
    Provide the mapping between following: information in database, *.json file, python object(ORM?). 
    '''
    video_info_dir = "video_list"
    TIMEFORMAT = "_%Y%m%d_%H-%M-%S"

    
    live_dir: str 
    live_db: Live_DB 

    def __init__(
        self, 
        online: bool,
        json_file = None, 
        engine = None
        ) -> None:
        '''
        Args:
        online: whether the object connects to the DB
        '''
        self.online_mode = online
        self.engine = engine
        self.db_url = None
        self.record_info = {}
        self.json_file:Optional[str] = json_file if json_file else None
        self.curr_video: Optional[Video_DB] = None
        # self.live_dir: Optional[str] = None
        # self.live_db: Optional[Live_DB] = None
        self.live_manager: Optional[LiveManager] = None
        
        
    def from_json(self):
        # self.live_dir = live_dir
        # self.engine = engine
        # self.live_db = Live_DB()
        # self.live_db.nickname = up_name
        # self.live_db.room_id = room_id
        # self.live_db.start_time = start_time if start_time else int(time.time())
        pass

    def set_record_info(self, version = 'v1'):
        info_json = {
            'version' : version,
            'time_format':self.TIMEFORMAT,
            'live_DB': self.live_db.to_dict(),
            'video_list': [video.to_dict() for video in self.live_db.videos],            
        }
        start_time = datetime.datetime.fromtimestamp(self.live_db.start_time)
        info_json.update({
            'year':start_time.strftime("%Y"),
            'month':start_time.strftime("%m"),
            'day':start_time.strftime("%d"),
            'hour':start_time.strftime("%H"),
            'up_name': self.live_db.nickname,
            'live_dir': os.path.abspath(self.live_dir),
            'Status':"Living"
        })
        self.record_info = info_json

    def dump_json(self, filename=None):
        '''
        If filename not provided, it will use self.json_file as filename.
        If self.json_name not exists, it will initialized in the directory self.live_dir+self.video_info_dir
        '''
        if filename is None:
            if self.json_file is None:
                self.json_file = os.path.join(
                    self.live_dir, 
                    self.video_info_dir,
                    self.live_db.nickname + self.live_db.time_create.strftime(self.TIMEFORMAT)+'.json')
            filename =  self.json_file
        os.makedirs(os.path.dirname(filename), exist_ok = True)
        with FileLock(filename+".lock"):
            with open(filename, 'w') as f:
                json.dump(self.record_info, f, indent=4) 
   
    # Try always regernerate the json
    def json_append_video(self, video: Optional[Video_DB] = None):
        '''
        If not video specified, append curr_video
        '''
        video = self.curr_video if video is None else video
        if video is None:
            raise Exception("curr_video is not initialized")
        self.record_info['video_list'].append(video.to_dict())
        print(f"{video.videoname} appended to record info")
    def json_live_end(self):
        self.record_info['Status'] = "Done"

    def from_database(self, live_id:int, engine):
        pass

    def from_new(
        self, 
        up_name: str, 
        room_id: int, 
        live_dir: str, 
        start_time:int = 0,
        ):
        '''
        Generate python object self.live_db:Live_DB from scratch
        '''
        self.live_dir = live_dir
        self.live_db = Live_DB()
        self.live_db.nickname = up_name
        self.live_db.room_id = room_id
        self.live_db.start_time = start_time if start_time else int(time.time())
        if self.online_mode:
            self.commit()
    def from_new_finalize(self, end_time):
        '''
        Update the python object self.live_db:Live_DB from scratch
        '''
        self.live_db.end_time = end_time  
        self.live_db.duration = end_time-self.live_db.start_time
        if self.online_mode:
            self.commit()

    def commit(self):
        if self.live_manager is None:
            self.live_manager = LiveManager(engine = self.engine, db = self.db_url)
        self.live_manager.add_live(self.live_db)

    # def __init__(self, engine, up_name,live_dir, roomid):
    #     self.live_dir = live_dir
    #     self.record_info_dir = os.path.join(self.live_dir, self.video_info_dir)
    #     os.makedirs(self.record_info_dir , exist_ok = True)
        
    #     self.up_name = up_name
    #     self.room_id = roomid
    #     self.time_create = datetime.datetime.now()
    #     self.end_time: Union[None, int] = None
    #     self.set_record_info()
        
    #     self.live_DB = Live_DB()
    #     self.update_live_DB()

    #     #curr_video needs to be initialized for websocket app works properly
    #     self.curr_video : Video = self.init_video()      

    #     self.num_danmu_total = 0
        

    def init_video(
        self, 
        filename:Optional[str]=None, 
        time_create:Optional[datetime.datetime]=None
        ):
        '''
        Used for initialize new video object, should be called in the presence of self.live. 
        '''
        if not self.live_db:
            raise Exception("Missing live_DB object")

        video = Video_DB()
        video.live = self.live_db
        video.time_create = datetime.datetime.now() if time_create is None else time_create
        if filename is not None:
            video.filename = filename
        else:
            video.filename = os.path.join(self.live_dir, self.live_db.nickname + video.time_create.strftime(self.TIMEFORMAT))
        video.videoname = video.filename +".flv"  
        video.subtitle_file = video.filename + ".ass"        
        video.danmu_end_time = [datetime.timedelta(seconds=0)]
        video.is_live = True  
        video.is_stored = False  
        
        self.curr_video = video
        if self.online_mode:
            self.commit()
        return self.curr_video
    
    def finalize_video(self, is_stored, end_time, size, storage_stg, video: Optional[Video_DB] = None):
        '''
        If not video specified, finalize curr_video
        '''
        video = self.curr_video if video is None else video

        if video is None:
            raise Exception("curr_video is not initialized")
        video.end_time = end_time 
        video.duration = end_time - video.start_time    
        video.size = size     
        video.is_live = False  
        video.is_stored = is_stored  
        video.deletion_type = storage_stg
        if self.online_mode:
            self.commit()




    # def danmu_rate(self, duration):
    #     prev_num = self.num_danmu_total
    #     time.sleep(duration)
    #     curr_num = self.num_danmu_total
    #     return curr_num - prev_num

