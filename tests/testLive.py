import datetime
from doctest import Example
import os
import unittest
import json
from tempfile import NamedTemporaryFile

from src.model.LiveDB import Live
from src.model.db import initialize_db

'''
python -m unittest tests.test1.TestFromNewOnline
'''


class BaseTestCase(unittest.TestCase):
    live : Live
    online:bool
    def setUp(self) -> None:
        self.skipTest("Skip the BaseTestCase that has not setUp defined")
    
    def test_from_json_to_json(self):
        """After reading from json file, it should dump out an exactly same json file'"""
        
        with NamedTemporaryFile('w+') as f1:
            self.live.set_json()
            self.live.dump_json(f1.name)
            temp_live = Live(online=False)
            temp_live.from_json(f1.name)
            with NamedTemporaryFile('w+t') as f2:
                temp_live.set_json()
                temp_live.dump_json(f2.name)
                f1.seek(0)
                f2.seek(0)
                assert f1.read() == f2.read()
    def test_initialization(self):
        '''
        Initialized object should be set to the provided value.
        '''
        live_attributes = ("nickname", "room_id", "start_time", "end_time")
        for x in live_attributes:
            y = self.live.live_db.__dict__[x]
            assert y == EXAMPLE1["live_DB"][x]
        
        video_attributes = ("start_time","video_basename", "video_directory", "subtitle_file",
        "is_live", "is_stored", "deletion_type", "end_time","duration","size")
        for idx,v in enumerate(self.live.live_db.videos):
            for x in video_attributes:
                y = v.__dict__[x]
                original = EXAMPLE1["video_list"][idx][x]
                assert y == original, f"Error on attribute: {x}, {y} versus {original}"
    
    # def testDumpout()

    def test_setServername(self):
        '''
        '''
        servername = "uploaded"
        self.live.video_servername(self.live.live_db.videos[1], servername)
        with NamedTemporaryFile('w+') as f1:
            self.live.set_json()
            assert self.live.json_output["video_list"][1]["server_name"] == servername
            

        if self.online:
            live = Live(online=True, engine=self.live.engine)
            live.from_database(EXAMPLE1["live_DB"]["live_id"])
            assert live.live_db.videos[1].server_name == servername


class TestFromJsonOffline(BaseTestCase):
    def setUp(self) -> None:
        """Call before every test case."""
        self.online = False
        self.live = Live(online=False)
        with NamedTemporaryFile('w+') as f:
            json.dump(EXAMPLE1,f,indent=4)
            f.seek(0)
            self.live.from_json(f.name)

    def test_Dump(self):
        with NamedTemporaryFile('w+') as f1:
            self.live.set_json()
            self.live.dump_json(f1.name)
            f1.seek(0)
            with NamedTemporaryFile('w+') as f2:
                json.dump(EXAMPLE1,f2,indent=4)
                f2.seek(0)
                assert f1.read() == f2.read()

class TestFromJsonOnline(BaseTestCase):
    def setUp(self) -> None:
        """Call before every test case."""
        self.online = True
        from sqlalchemy import create_engine
        engine = create_engine("sqlite+pysqlite:///:memory:", echo=False, future=True)
        initialize_db(engine)
        live = Live(online=True, engine=engine)
        live.from_new(
            up_name = EXAMPLE1["live_DB"]["nickname"], 
            room_id = EXAMPLE1["live_DB"]["room_id"] , 
            live_dir = EXAMPLE1["video_list"][0]["video_directory"], 
            start_time = EXAMPLE1["live_DB"]["start_time"],
        )
        for video in EXAMPLE1["video_list"]:
            filename = os.path.join(video["video_directory"], video["video_basename"]).split(".")[0]
            time_create = datetime.datetime.fromtimestamp(video["start_time"])
            video_i = live.init_video(filename, time_create)
            live.finalize_video(
                video["is_stored"],
                video["end_time"],
                video["size"],
                video["deletion_type"],
                video_i
            )
        live.from_new_finalize(EXAMPLE1["live_DB"]["end_time"])
        with NamedTemporaryFile('w+') as f:
            json.dump(EXAMPLE1,f,indent=4)
            f.seek(0)
            
            self.live = Live(online=True, engine=engine)
            self.live.from_json(f.name)
        


class TestFromNewOnline(BaseTestCase):
    def setUp(self) -> None:
        """Call before every test case."""
        self.online = True
        from sqlalchemy import create_engine
        engine = create_engine("sqlite+pysqlite:///:memory:", echo=False, future=True)
        initialize_db(engine)
        self.live = Live(online=True, engine=engine)
        self.live.from_new(
            up_name = EXAMPLE1["live_DB"]["nickname"], 
            room_id = EXAMPLE1["live_DB"]["room_id"] , 
            live_dir = EXAMPLE1["video_list"][0]["video_directory"], 
            start_time = EXAMPLE1["live_DB"]["start_time"],
        )
        for video in EXAMPLE1["video_list"]:
            filename = os.path.join(video["video_directory"], video["video_basename"]).split(".")[0]
            time_create = datetime.datetime.fromtimestamp(video["start_time"])
            video_i = self.live.init_video(filename, time_create)
            self.live.finalize_video(
                video["is_stored"],
                video["end_time"],
                video["size"],
                video["deletion_type"],
                video_i
            )
        self.live.from_new_finalize(EXAMPLE1["live_DB"]["end_time"])

class TestFromDB(BaseTestCase):
    def setUp(self) -> None:
        """Call before every test case."""
        self.online = True
        from sqlalchemy import create_engine
        engine = create_engine("sqlite+pysqlite:///:memory:", echo=False, future=True)
        initialize_db(engine)
        live = Live(online=True, engine=engine)
        live.from_new(
            up_name = EXAMPLE1["live_DB"]["nickname"], 
            room_id = EXAMPLE1["live_DB"]["room_id"] , 
            live_dir = EXAMPLE1["video_list"][0]["video_directory"], 
            start_time = EXAMPLE1["live_DB"]["start_time"],
        )
        for video in EXAMPLE1["video_list"]:
            filename = os.path.join(video["video_directory"], video["video_basename"]).split(".")[0]
            time_create = datetime.datetime.fromtimestamp(video["start_time"])
            live.init_video(filename, time_create)
            live.finalize_video(
                video["is_stored"],
                video["end_time"],
                video["size"],
                video["deletion_type"]
            )
        live.from_new_finalize(EXAMPLE1["live_DB"]["end_time"])
        self.live = Live(online=True, engine=engine)
        self.live.from_database(EXAMPLE1["live_DB"]["live_id"])

class TestFromNewOffline(BaseTestCase):
    def setUp(self) -> None:
        """Call before every test case."""
        self.online = False
        self.live = Live(online=False)
        self.live.from_new(
            up_name = EXAMPLE1["live_DB"]["nickname"], 
            room_id = EXAMPLE1["live_DB"]["room_id"] , 
            live_dir = EXAMPLE1["video_list"][0]["video_directory"], 
            start_time = EXAMPLE1["live_DB"]["start_time"],
        )
        for video in EXAMPLE1["video_list"]:
            filename = os.path.join(video["video_directory"], video["video_basename"]).split(".")[0]
            time_create = datetime.datetime.fromtimestamp(video["start_time"])
            self.live.init_video(filename, time_create)
            self.live.finalize_video(
                video["is_stored"],
                video["end_time"],
                video["size"],
                video["deletion_type"]
            )
        self.live.from_new_finalize(EXAMPLE1["live_DB"]["end_time"])



if __name__ == "__main__":
    unittest.main()


EXAMPLE1 = {
    "version": "v1",
    "time_format": "_%Y%m%d_%H-%M-%S",
    "live_DB": {
        "nickname": "test",
        "room_id": 22259479,
        "start_time": 1657148862,
        "live_id": 1,
        "is_uploaded": False,
        "end_time": 1657158862
    },
    "video_list": [
        {
            "start_time": 1657148863,
            "video_basename": "test_20220707_07-07-43.flv",
            "video_directory": "Videos/test",
            "subtitle_file": "Videos/test/test_20220707_07-07-43.ass",
            "is_live": False,
            "is_stored": True,
            "live_id": 1,
            "video_id": 1,
            "deletion_type": 0,
            "end_time": 1657148880,
            "duration": 17,
            "size": 22282240
        },
        {
            "start_time": 1657148881,
            "video_basename": "test_20220707_07-08-01.flv",
            "video_directory": "Videos/test",
            "subtitle_file": "Videos/test/test_20220707_07-08-01.ass",
            "is_live": False,
            "is_stored": True,
            "live_id": 1,
            "video_id": 2,
            "deletion_type": 0,
            "end_time": 1657148910,
            "duration": 29,
            "size": 36503552
        },
        {
            "start_time": 1657148911,
            "video_basename": "test_20220707_07-08-31.flv",
            "video_directory": "Videos/test",
            "subtitle_file": "Videos/test/test_20220707_07-08-31.ass",
            "is_live": False,
            "is_stored": True,
            "live_id": 1,
            "video_id": 3,
            "deletion_type": 0,
            "end_time": 1657148940,
            "duration": 29,
            "size": 33095680
        },
        {
            "start_time": 1657148941,
            "video_basename": "test_20220707_07-09-01.flv",
            "video_directory": "Videos/test",
            "subtitle_file": "Videos/test/test_20220707_07-09-01.ass",
            "is_live": False,
            "is_stored": True,
            "live_id": 1,
            "video_id": 4,
            "deletion_type": 0,
            "end_time": 1657148970,
            "duration": 29,
            "size": 38469632
        }
    ],
    "year": "2022",
    "month": "07",
    "day": "06",
    "hour": "18",
    "up_name": "test",
    "Status": "Living"
}