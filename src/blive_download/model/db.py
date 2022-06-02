# pylint: disable=no-member
from typing import Union
from sqlalchemy import ForeignKey, Column, Integer, String, Boolean

from sqlalchemy.orm import registry
mapper_registry = registry()
Base = mapper_registry.generate_base()

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
    live_id = Column(Integer, primary_key=True)
    nickname = Column(String, nullable=False)
    room_id = Column(Integer, nullable=False)
    start_time = Column(Integer, nullable=False)
    end_time = Column(Integer)
    duration: Union[Column, int] = Column(Integer)
    # is_live = Column(Boolean, nullable=False, default = False)
    is_uploaded = Column(Boolean, nullable=False, default = False)

from enum import Enum

class storage_stg(Enum):
    DEFAULT = 0   #
    NEVER = 1   #Will not be deleted
    UNTIL_UPLOAD = 2    #After been uploaded (has a server_name), it becomes DEFAULT

class Video_DB(Base):  # type: ignore
    __tablename__ = 'Video'
    video_id = Column(Integer, primary_key=True)
    videoname = Column(String, nullable=False)
    live_id = Column(Integer, ForeignKey('Live.live_id'), nullable=False)
    start_time = Column(Integer, nullable=False)
    end_time = Column(Integer)
    duration = Column(Integer)
    size = Column(Integer)
    is_live = Column(Boolean, nullable=False)
    deletion_type = Column(Integer, nullable=False, default=0)
    is_stored = Column(Boolean, nullable=False)
    server_name = Column(String)
    
    def __repr__(self) -> str:
        return repr({x:y for x,y in self.__dict__.items() if not x.startswith('_')})

# Danmu protocal https://zhuanlan.zhihu.com/p/37874066
class Danmu_DB(Base):  # type: ignore
    __tablename__ = 'Danmu'
    danmu_id = Column(Integer, primary_key=True)
    live_id = Column(Integer, ForeignKey('Live.live_id'), nullable=False)
    video_id = Column(Integer)
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
    mapper_registry.metadata.create_all(engine)
    return engine

class TableManager():
    def __init__(self, engine) -> None:
        self.engine = engine