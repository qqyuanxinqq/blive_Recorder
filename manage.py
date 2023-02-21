from src.model import connect_db, RecorderManager, VideoManager
from src.utils import configCheck


CONFIG_PATH = "config.yaml"

conf = configCheck(CONFIG_PATH)
engine = connect_db(conf["_default"]["Database"]["link"])
recorderM = RecorderManager(engine = engine)
videoM = VideoManager(engine = engine)

def add_task(up_name):
    recorderM.add_task(up_name)

def kill_task(up_name):
    recorderM.kill_task(up_name)

def list_task():
    pids = [(i.nickname, i.pid) for i in recorderM.get_task() if i.pid != 0]
    print(pids)