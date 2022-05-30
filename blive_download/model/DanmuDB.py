# pylint: disable=no-member
from sqlalchemy.dialects.sqlite import insert

from .db import Danmu_DB, TableManager

class DanmuManager(TableManager):
    def insert_danmu(self, danmu_DB_list):
        with self.engine.begin() as conn:
            conn.execute(
                insert(Danmu_DB.__table__),
                danmu_DB_list
                )
