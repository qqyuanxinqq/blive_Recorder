# pylint: disable=no-member
from sqlalchemy.orm import Session

from .db import Live_DB, TableManager
from ...utils import Retry

@Retry(max_retry = 5, interval = 10).decorator
class LiveManager(TableManager):
    def update_live(self, live: Live_DB):
        with Session(self.engine) as session:
            session.expire_on_commit = False
            session.add(live)
            session.commit()
        return live