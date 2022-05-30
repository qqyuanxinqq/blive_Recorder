# pylint: disable=no-member
from sqlalchemy.orm import Session

from .db import Live_DB, TableManager

class LiveManager(TableManager):
    def update_live(self, live: Live_DB):
        with Session(self.engine) as session:
            session.expire_on_commit = False
            session.add(live)
            session.commit()
        return live