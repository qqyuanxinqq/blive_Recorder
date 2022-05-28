import blive_download.table
from blive_download.utils import configCheck


conf = configCheck()
engine = blive_download.table.connect_db(conf["_default"]["Database"])


def add_task(up_name):
    blive_download.table.add_task(engine, up_name)


def kill_task(up_name):
    blive_download.table.kill_task(engine, up_name)

def list_task():
    pids = [(i.nickname, i.pid) for i in blive_download.table.get_task(engine) if i.pid != 0]
    print(pids)

