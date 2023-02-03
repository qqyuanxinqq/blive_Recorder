import datetime, time
import logging
import os
import json
from typing import Any, Optional

from filelock import FileLock
from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import Live_DB, TableManager, Video_DB
from ..utils import Retry

@Retry(max_retry = 5, interval = 10).decorator
class LiveManager(TableManager):
    def add_live(self, live: Live_DB) -> Live_DB:
        with Session(self.engine) as session:
            session.expire_on_commit = False
            session.add(live)
            session.commit()
            temp = live.videos  #Actively access its children to eager load
        return live
    def read_live_2(self, live_id: int):
        stmt = select(Live_DB).where(Live_DB.live_id == live_id)
    def read_live(self, live_id: int) -> Live_DB:
        with Session(self.engine) as session:
            session.expire_on_commit = False
            live = session.get(Live_DB, live_id)
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
        self.json_output = {}
        self.json_input = {}
        self.json_file:Optional[str] = json_file if json_file else None
        self.curr_video: Optional[Video_DB] = None
        # self.live_dir: Optional[str] = None
        # self.live_db: Optional[Live_DB] = None
        self.live_manager: Optional[LiveManager] = None
        
        
    def from_json(self, filename: Optional[str] = None):
        '''
        Generate python ORM object self.live_db:Live_DB from dumped json file.
        Note: the object is not mapped to the database.

        If filename not provided, it will use self.json_file as filename.
        If self.json_name not exists, it will initialized in the directory self.live_dir+self.video_info_dir
        '''
        if filename is None:
            if self.json_file is None:
                raise Exception("Json file is not provided as filename or self.json_file")
            filename =  self.json_file
        if not os.path.exists(filename):
            raise Exception("Provided *.json path is not valid")

        with FileLock(filename + '.lock'):
            with open(filename, 'r') as f:
                self.json_input = json.load(f)
        
        if self.json_input['version'] == 'v1':
            if self.online_mode:
                self.from_database(self.json_input['live_DB']['live_id'])
            else: 
                self.live_db = Live_DB(**self.json_input['live_DB'])
                for video in self.json_input['video_list']:
                    self.live_db.videos.append(Video_DB(**video))

    def video_servername(self, video: Video_DB, server_name):
        '''
        
        '''
        video.server_name = server_name
        if self.online_mode:
            self.commit()

    def set_json(self, version = 'v1'):
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
            'live_title': self.live_db.live_title,
            # 'live_dir': os.path.abspath(self.live_dir),
            'Status':"Done" if self.live_db.end_time else "Living"
        })
        self.json_output = info_json

    def dump_json(self, filename=None):
        '''
        If filename not provided, it will use self.json_file as filename.
        If self.json_name not exists, it will be initialized in the directory self.live_dir+self.video_info_dir, 
        with basename self.live_db.nickname + self.live_db.time_create.strftime(self.TIMEFORMAT)+'.json'
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
                json.dump(self.json_output, f, indent=4) 
   
    # Try always regernerate the json
    def json_append_video(self, video: Video_DB):
        '''
        Append video specified
        '''
        if video is None:
            raise Exception("Video is not initialized")
        self.json_output['video_list'].append(video.to_dict())
        print(f"{video.videoname} appended to record info")

    def from_database(self, live_id:int, engine:Optional[Any] = None):
        if engine is not None:
            self.engine = engine
        elif self.engine is None:
            raise Exception("Engine object is not provided.")

        if self.live_manager is None:
            self.live_manager = LiveManager(engine = self.engine, db = self.db_url)
        self.live_db = self.live_manager.read_live(live_id)

    def from_new(
        self, 
        up_name: str, 
        room_id: int, 
        live_dir: str, 
        start_time:int = 0,
        live_title:str = ""
        ):
        '''
        Generate python ORM object self.live_db:Live_DB from scratch
        '''
        self.live_dir = live_dir
        self.live_db = Live_DB()
        self.live_db.nickname = up_name
        self.live_db.room_id = room_id
        self.live_db.live_title = live_title
        self.live_db.start_time = start_time if start_time else int(time.time())
        if self.online_mode:
            self.commit()
    def from_new_finalize(self, end_time):
        '''
        Update the python object self.live_db:Live_DB from scratch
        '''
        self.live_db.end_time = end_time  
        # self.live_db.duration = end_time-self.live_db.start_time
        if self.online_mode:
            self.commit()

    def commit(self):
        try:
            if self.live_manager is None:
                self.live_manager = LiveManager(engine = self.engine, db = self.db_url)
            self.live_manager.add_live(self.live_db)
        except Exception as e:
            logging.exception(e)

    def init_video(
        self, 
        filename:Optional[str]=None, 
        time_create:Optional[datetime.datetime]=None
        ) -> Video_DB:
        '''
        Used for initialize new video object, should be called in the presence of self.live. 
        This new will video will be attached to the live object UNTIL finalize_video(is_stored = True) is called.
        '''
        if not self.live_db:
            raise Exception("Missing live_DB object")

        video = Video_DB()
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
        
        if self.online_mode:
            self.commit()
        return video
    
    def finalize_video(self, is_stored:bool, end_time:int, size:int, storage_stg:int, video: Video_DB) -> Video_DB:
        '''
        Finalize video specified
        '''
        
        if video is None:
            print("Video is not initialized")
            return Video_DB()
        video.end_time = end_time 
        video.duration = end_time - video.start_time    
        video.size = size     
        video.is_live = False  
        video.is_stored = is_stored  
        video.deletion_type = storage_stg

        if video.is_stored:
            #Avoid unnecessary attachment to the live object in database
            video.live = self.live_db   
        else:
            if os.path.exists(video.subtitle_file):
                # Delete unnecessary ass files. 
                os.remove(video.subtitle_file)

        if self.online_mode:
            self.commit()

        return video




    # def danmu_rate(self, duration):
    #     prev_num = self.num_danmu_total
    #     time.sleep(duration)
    #     curr_num = self.num_danmu_total
    #     return curr_num - prev_num

