# pylint: disable=no-member
import os
from typing import Any, Dict, Optional, Union, List
import datetime
from sqlalchemy import ForeignKey, Column, Integer, String, Boolean

from sqlalchemy.orm import registry
from sqlalchemy.orm import relationship

mapper_registry = registry()
Base = mapper_registry.generate_base()
from ..utils import Retry

class Recorder_DB(Base):  # type: ignore
    __tablename__ = 'Up_name'

    # up_name = Column(String, nullable=False)
    nickname = Column(String, primary_key=True, nullable=False)
    added_time = Column(Integer)
    
    should_running = Column(Boolean, default = False)
    is_live = Column(Boolean, nullable=False, default = False)
    pid = Column(Integer, nullable=False, default = 0)  #pid==0 indicates the Process is not running 

class Live_DB(Base):  # type: ignore
    __tablename__ = 'Live'

    @property
    def time_create(self) -> datetime.datetime: 
        return datetime.datetime.fromtimestamp(self.start_time)
    @time_create.setter
    def time_create(self, dt: datetime.datetime):
        self.start_time = int(datetime.datetime.timestamp(dt))
    
    start_time: int = Column(Integer, nullable=False)     #type:ignore
    live_id = Column(Integer, primary_key=True)
    nickname: str = Column(String, nullable=False) #type:ignore
    room_id:int = Column(Integer, nullable=False)  #type:ignore
    end_time = Column(Integer)
    # is_live = Column(Boolean, nullable=False, default = False)
    is_uploaded = Column(Boolean, nullable=False, default = False)
    videos:List = relationship("Video_DB", back_populates="live")

    def to_dict(self) -> Dict[str, Any]:
        dict_temp = {}
        for x,y in self.__dict__.items():
            if x.startswith('_'):
                continue
            elif x in ("videos",):
                continue
            else:
                dict_temp.update({x:y})
        return dict_temp

from enum import Enum
class storage_stg(Enum):
    DEFAULT = 0   #
    NEVER = 1   #Will not be deleted
    UNTIL_UPLOAD = 2    #After been uploaded (has a server_name), it becomes DEFAULT

class Video_DB(Base):
    __tablename__ = 'Video'
    
    @property
    def time_create(self) -> datetime.datetime: 
        return datetime.datetime.fromtimestamp(self.start_time)
    @time_create.setter
    def time_create(self, dt: datetime.datetime):
        self.start_time = int(datetime.datetime.timestamp(dt))
    
    @property
    def up_name(self) -> str:
        return self.live.nickname

    video_id = Column(Integer, primary_key=True)
    live_id = Column(Integer, ForeignKey('Live.live_id'), nullable=False)
    start_time: int = Column(Integer, nullable=False)     #type:ignore
    
    @property
    def videoname(self) -> str: 
        return os.path.join(self.video_directory,self.video_basename)
    @videoname.setter
    def videoname(self, videopath: str):
        self.video_basename = os.path.basename(videopath)
        self.video_directory = os.path.dirname(videopath)

    video_basename: str = Column(String, nullable=True)  #type:ignore
    video_directory: str = Column(String, nullable=False)   #type:ignore

    subtitle_file: str = Column(String)     #type:ignore
    end_time:int = Column(Integer)   #type:ignore
    duration:int = Column(Integer)  #type:ignore
    size:int = Column(Integer)  #type:ignore
    is_live:bool = Column(Boolean, nullable=False)    #type:ignore
    deletion_type: int = Column(Integer, nullable=False, default=0)    #type:ignore
    is_stored: bool = Column(Boolean, nullable=False)    #type:ignore
    server_name = Column(String)
    
    live: Live_DB = relationship("Live_DB", back_populates = "videos")
    filename: str
    danmu_end_time: List[datetime.timedelta]

    def to_dict(self) -> Dict[str, Any]:
        dict_temp = {}
        for x,y in self.__dict__.items():
            if x.startswith('_'):
                continue
            elif x in ("filename", "danmu_end_time", "live"):
                continue
            # elif isinstance(y, (int, float, str, bool))
            else:
                dict_temp.update({x:y})
        return dict_temp
    
    def __repr__(self) -> str:
        return "Object" + repr({x:y for x,y in self.__dict__.items() if not x.startswith('_')})

# Danmu protocal https://zhuanlan.zhihu.com/p/37874066
class Danmu_DB(Base):  # type: ignore
    __tablename__ = 'Danmu'
    danmu_id = Column(Integer, primary_key=True)
    live_id = Column(Integer, ForeignKey('Live.live_id'), nullable=False)
    video_basename = Column(String)
    content = Column(String, nullable=False)
    start_time = Column(Integer, nullable=False)
    uid = Column(Integer, nullable = False)
    username = Column(String, nullable=False)
    type = Column(String, nullable=False)
    color = Column(Integer)   #RGB in decimal
    price = Column(Integer)
    
class User_DB(Base):  # type: ignore
    __tablename__ = 'User'
    uid = Column(Integer, primary_key=True)
    username = Column(String, nullable=False) 
    symbol = Column(String)
    symbol_UP_name = Column(String)
    symbol_level = Column(Integer)


class Log_DB(Base):  # type: ignore
    __tablename__ = 'Log'
    rowid = Column(Integer, primary_key=True)
    start_time = Column(Integer, nullable=False)
    type = Column(String, nullable=False)
    content = Column(String, nullable=False)

def drop_table(table, engine):
    table.drop(engine)

def clear_status(engine):
    drop_table(Recorder_DB.__table__, engine)

from sqlalchemy import create_engine

@Retry(max_retry = 5, interval = 5).decorator
def connect_db(target:str):
    # import logging
    # logging.basicConfig()
    # logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)
    # logging.getLogger("sqlalchemy.pool").setLevel(logging.DEBUG)

    engine = create_engine("sqlite+pysqlite:///{}".format(target), 
                            future=True, 
                            # echo = True, 
                            # echo_pool = "debug"
                            )
    initialize_db(engine)
    return engine
    
def initialize_db(engine):
    mapper_registry.metadata.create_all(engine)

class TableManager():
    engine: Any
    def __init__(self, engine = None, db = None) -> None:
        if engine is not None:
            self.engine = engine
        elif db is not None:
            self.engine = connect_db(db)
        else: 
            raise Exception("Connection to DB is not provided")
        