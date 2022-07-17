# pylint: disable=no-member
from sqlalchemy import ForeignKey, Column, Integer, String, Boolean

from sqlalchemy.orm import registry
mapper_registry = registry()
Base = mapper_registry.generate_base()

class Recorder_DB(Base):
    __tablename__ = 'Up_name'

    # up_name = Column(String, nullable=False)
    nickname = Column(String, primary_key=True, nullable=False)
    added_time = Column(Integer)
    
    should_running = Column(Boolean, default = False)
    is_live = Column(Boolean, nullable=False, default = False)
    pid = Column(Integer, nullable=False, default = 0)

class Live_DB(Base):
    __tablename__ = 'Live'
    live_id = Column(Integer, primary_key=True)
    nickname = Column(String, nullable=False)
    room_id = Column(Integer, nullable=False)
    start_time = Column(Integer, nullable=False)
    end_time = Column(Integer)
    duration = Column(Integer)
    # is_live = Column(Boolean, nullable=False, default = False)
    is_uploaded = Column(Boolean, nullable=False, default = False)

class Video_DB(Base):
    __tablename__ = 'Video'
    video_id = Column(Integer, primary_key=True)
    videoname = Column(String, nullable=False)
    live_id = Column(Integer, ForeignKey('Live.live_id'), nullable=False)
    start_time = Column(Integer, nullable=False)
    end_time = Column(Integer)
    duration = Column(Integer)
    size = Column(Integer)
    is_live = Column(Boolean, nullable=False)
    is_stored = Column(Boolean, nullable=False)
    server_name = Column(String)


    # Danmu protocal https://zhuanlan.zhihu.com/p/37874066
class Danmu_DB(Base):
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
    


class User_DB(Base):
    __tablename__ = 'User'
    uid = Column(Integer, primary_key=True)
    username = Column(String, nullable=False) 
    symbol = Column(String)
    symbol_UP_name = Column(String)
    symbol_level = Column(Integer)


class Log_DB(Base):
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

    engine = create_engine("sqlite+pysqlite:///{}".format(target), future=True, echo = True, echo_pool = "debug")
    mapper_registry.metadata.create_all(engine)
    return engine


from time import time
from typing import List

from sqlalchemy import select, update
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.orm import Session

def get_task(engine) -> List:
    '''
    Input engine object of database
    Output list of Recorder_DB objects in 'Up_name' table
    '''
    with Session(engine) as session:
        result = session.execute(
            select(Recorder_DB)
            )
        rtn=[row[0] for row in result]
    return rtn

    # blive_download.table.UP_DB.__table__.c.keys()
    # with engine.begin() as conn:
    #     result = conn.execute(
    #         select(UP_DB.__table__)
    #         )
    #     return result.rowcount
def add_task(engine, nickname: str) -> str:

    '''
    Input: engine object of database, and nickname
    Return: nickname if success
    '''
    with engine.begin() as conn:
        result = conn.execute(
            insert(Recorder_DB.__table__). 
            values({"nickname": nickname, "added_time":int(time()), "should_running": True}).
            on_conflict_do_update(index_elements = ["nickname"], set_= {"added_time":int(time()), "should_running": True})
            )
        return result.inserted_primary_key[0]

def kill_task(engine, nickname: str) -> int:
    '''
    Input engine object of database, and nickname
    Return: Number of tuples been updated, normally should be 1
    '''
    with engine.begin() as conn:
        result = conn.execute(
            update(Recorder_DB.__table__).  
            where(Recorder_DB.__table__.c.nickname == nickname).
            values({"should_running": False})
            )
        return result.rowcount

def update_pid(engine, nickname: str, pid)  -> int:
    if not pid:
        pid = 0

    with engine.begin() as conn:
        result = conn.execute(
            update(Recorder_DB.__table__).  
            where(Recorder_DB.__table__.c.nickname == nickname).
            values({"pid": pid})
            )
        return result.rowcount


def update_live(engine, live: Live_DB):
    with Session(engine) as session:
        session.expire_on_commit = False
        session.add(live)
        session.commit()
    return live

def update_video(engine, video: Video_DB):
    with Session(engine) as session:
        session.expire_on_commit = False
        session.add(video)
        session.commit()
    return video



def insert_danmu(engine, danmu_DB_list):
    with engine.begin() as conn:
        conn.execute(
            insert(Danmu_DB.__table__),
            danmu_DB_list
            )
        # return result.rowcount    #Avoid unnecessary ocuupation to the locking connection.