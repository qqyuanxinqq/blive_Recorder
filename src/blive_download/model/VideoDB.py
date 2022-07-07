# pylint: disable=no-member

from typing import Iterable, List
from sqlalchemy.orm import Session
from sqlalchemy import select
from .db import Live_DB, TableManager, Video_DB
from ...utils import Retry

# class Video_DB(Video_DB):
#     time_create: datetime.datetime
#     up_name: str
#     live_dir: str
#     filename: str
#     ass_name: str
#     danmu_end_time: List[datetime.timedelta]

class VideoManager(TableManager):
    @Retry(max_retry = 5, interval = 10).decorator
    def update_videos(self, videos: Iterable[Video_DB]) -> Iterable[Video_DB]:
        if not videos:
            return videos

        with Session(self.engine) as session:
            session.expire_on_commit = False
            for video in videos:
                session.add(video)
            session.commit()
        return videos
    @Retry(max_retry = 5, interval = 10, default = []).decorator
    def get_stored_videos(self) -> List[Video_DB]:
        '''
        Input Engine
        Output a list of Video_DB objects
        '''
        with Session(self.engine) as session:
            session.expire_on_commit = False
            result = session.execute(
                select(Video_DB).
                join(Live_DB).
                where(Video_DB.is_stored == True).order_by(Live_DB.start_time)
                )
            rtn=[row[0] for row in result]
        return rtn

# def get_stored_videos(engine) -> List[Video_DB]:
#     '''
#     Input Engine
#     Output a list of Video_DB objects
#     '''
#     with Session(engine) as session:
#         result = session.execute(
#             select(Video_DB).
#             where(Video_DB.is_stored == True).order_by(Video_DB.start_time)
#             )
#         rtn=[row[0] for row in result]
#     return rtn