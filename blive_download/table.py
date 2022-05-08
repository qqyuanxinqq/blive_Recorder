from sqlalchemy import ForeignKey, Column, Integer, String, Boolean
from sqlalchemy import create_engine

from sqlalchemy.orm import registry
mapper_registry = registry()
Base = mapper_registry.generate_base()

class UP_DB(Base):
    __tablename__ = 'Up_name'

    # up_name = Column(String, nullable=False)
    nickname = Column(String, primary_key=True, nullable=False)
    added_time = Column(Integer)
    
    is_running = Column(Boolean, default = False)
    should_running = Column(Boolean, default = False)
    is_live = Column(Boolean, nullable=False)

class Live_DB(Base):
    __tablename__ = 'Live'
    live_id = Column(Integer, primary_key=True)
    nickname = Column(String, ForeignKey("Up_name.nickname"), nullable=False)
    room_id = Column(Integer, nullable=False)
    start_time = Column(Integer, nullable=False)
    end_time = Column(Integer)
    is_live = Column(Boolean, nullable=False)

class Video_DB(Base):
    __tablename__ = 'Video'
    video_id = Column(Integer, primary_key=True)
    live_id = Column(Integer, ForeignKey('Live.live_id'), nullable=False)
    start_time = Column(Integer, nullable=False)
    end_time = Column(Integer)
    size = Column(Integer)
    is_live = Column(Boolean, nullable=False)

    # https://zhuanlan.zhihu.com/p/37874066
class Danmu_DB(Base):
    __tablename__ = 'Danmu'
    danmu_id = Column(Integer, primary_key=True)
    video_id = Column(Integer, ForeignKey('Video.video_id'))
    content = Column(String, nullable=False)
    start_time = Column(Integer, nullable=False)
    uid = Column(Integer, ForeignKey('User.uid'))
    type = Column(String, nullable=False)
    


class User_DB(Base):
    __tablename__ = 'User'
    rowid = Column(Integer, primary_key=True)
    uid = Column(Integer, nullable=False)
    username = Column(String, nullable=False) 
    symbol = Column(String)
    symbol_level = Column(Integer)


class Log_DB(Base):
    __tablename__ = 'Log'
    rowid = Column(Integer, primary_key=True)
    start_time = Column(Integer, nullable=False)
    type = Column(String, nullable=False)
    content = Column(String, nullable=False)

def create_db(target):
    engine = create_engine("sqlite+pysqlite:///{}".format(target), echo=True, future=True)
    mapper_registry.metadata.create_all(engine)
    return engine


def add_task():
    pass

def kill_task():
    pass
