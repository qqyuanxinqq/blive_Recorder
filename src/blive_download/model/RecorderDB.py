# pylint: disable=no-member
from time import time
from typing import List

from sqlalchemy import select, update
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.orm import Session

from .db import Recorder_DB, TableManager
from ...utils import Retry

class RecorderManager(TableManager):
    @Retry(max_retry = 5, interval = 10).decorator
    def get_task(self) -> List:
        '''
        Input engine object of database
        Output list of Recorder_DB objects in 'Up_name' table
        '''
        with Session(self.engine) as session:
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
    @Retry(max_retry = 5, interval = 10).decorator
    def add_task(self, nickname: str) -> str:

        '''
        Input: engine object of database, and nickname
        Return: nickname if success
        '''
        with self.engine.begin() as conn:
            result = conn.execute(
                insert(Recorder_DB.__table__). 
                values({"nickname": nickname, "added_time":int(time()), "should_running": True}).
                on_conflict_do_update(index_elements = ["nickname"], set_= {"added_time":int(time()), "should_running": True})
                )
            return result.inserted_primary_key[0]
    @Retry(max_retry = 5, interval = 10).decorator
    def kill_task(self, nickname: str) -> int:
        '''
        Input engine object of database, and nickname
        Return: Number of tuples been updated, normally should be 1
        '''
        with self.engine.begin() as conn:
            result = conn.execute(
                update(Recorder_DB.__table__).  
                where(Recorder_DB.__table__.c.nickname == nickname).
                values({"should_running": False})
                )
            return result.rowcount
    @Retry(max_retry = 5, interval = 10).decorator
    def update_pid(self, nickname: str, pid)  -> int:
        if not pid:
            pid = 0

        with self.engine.begin() as conn:
            result = conn.execute(
                update(Recorder_DB.__table__).  
                where(Recorder_DB.__table__.c.nickname == nickname).
                values({"pid": pid})
                )
            return result.rowcount

