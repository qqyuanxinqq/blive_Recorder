import blive_download.table
from blive_download.record import configCheck


conf = configCheck()
engine = blive_download.table.create_db(conf["_default"]["Database"])


def add_task(up_name):
    blive_download.table.add_task(engine, up_name)


def kill_task(up_name):
    blive_download.table.kill_task(engine, up_name)
