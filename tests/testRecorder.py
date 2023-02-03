import json
import logging
from multiprocessing import Process
import os
import signal
from tempfile import NamedTemporaryFile, TemporaryDirectory
from threading import Thread
from time import sleep, time
import unittest

from src.blive_download.recorder import Recorder
from src.utils.myproc import Myproc

EXAMPLE_CONFIG1 = {
    "_default": {
        "Enabled_recorder": ["test1"],
        "Database": "test.db",
        "upload_configuration": "upload_config.json",
        "name": "_default",
        "room_id": "",
        "divide_video": ["duration", 10],
        "upload_flag": 0,
        "flvtag_update": 1,
        "path": "Videos/",
        "storage_stg": 0
    },
    "test1": {
        "name": "test1",
        "room_id": "3"
    }
}

class TestRecorder(unittest.TestCase):
    def setUp(self) -> None:
        """Call before every test case."""
        self.dir = TemporaryDirectory()
        self.config_file = NamedTemporaryFile("w+")
        for k in ["Database","upload_configuration", "path"]:
            if EXAMPLE_CONFIG1["_default"].get(k):
                EXAMPLE_CONFIG1["_default"][k] = os.path.join(self.dir.name, EXAMPLE_CONFIG1["_default"][k])
        self.config = EXAMPLE_CONFIG1
        json.dump(self.config, self.config_file)
        self.config_file.seek(0)

        self.recorder = Recorder("test1")
        self.recorder.init_from_json(self.config_file.name)
        self.p = Process(target=self.recorder.run)
        self.p.start()
        sleep(15)


    def tearDown(self) -> None:
        if self.p.is_alive():
            self.p.terminate()
        
        sleep(2)
        self.config_file.close()
        self.dir.cleanup()


    def test_run(self):
        
        for _ in range(30):
            sleep(1)
            assert self.p.is_alive(), "recorder.run stopped"
            files = os.listdir(os.path.join(self.config["_default"]["path"],"test1"))
            assert files, f"No file in {self.config['_default']['path']}"
            assert "video_list" in files, f"video_list folder not in {self.config['_default']['path']}"

            files = os.listdir(os.path.join(self.config["_default"]["path"],"test1","video_list"))
            for jsonfile in [file for file in files if file.endswith('.json')]:
                with open(os.path.join(self.config["_default"]["path"],"test1","video_list",jsonfile), 'r') as f:
                    config:dict = json.load(f)
                    for item in config["video_list"]:
                        assert item["is_stored"]
                        assert os.path.exists(os.path.join(item["video_directory"], item["video_basename"]))


        # Check items in DB

    def test_ending(self):

        if self.p.pid:
            os.kill(self.p.pid, signal.SIGINT)
            sleep(5)
        if self.p.is_alive():
            self.p.terminate()

        files = os.listdir(os.path.join(self.config["_default"]["path"],"test1","video_list"))
        for jsonfile in [file for file in files if file.endswith('.json')]:
            with open(os.path.join(self.config["_default"]["path"],"test1","video_list",jsonfile), 'r') as f:
                config:dict = json.load(f)
                for item in config["video_list"]:
                    assert item["is_stored"]
        
            


