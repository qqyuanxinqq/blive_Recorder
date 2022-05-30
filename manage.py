from blive_download.model import connect_db, RecorderManager
from blive_download.model.VideoDB import VideoManager
from blive_download.utils import configCheck


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