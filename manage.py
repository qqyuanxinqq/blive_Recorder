from src.blive_download.model import connect_db, RecorderManager, VideoManager
from src.utils import configCheck


conf = configCheck()
engine = connect_db(conf["_default"]["Database"])
recorderM = RecorderManager(engine)
videoM = VideoManager(engine)

def add_task(up_name):
    recorderM.add_task(up_name)


def kill_task(up_name):
    recorderM.kill_task(up_name)

def list_task():
    pids = [(i.nickname, i.pid) for i in recorderM.get_task() if i.pid != 0]
    print(pids)