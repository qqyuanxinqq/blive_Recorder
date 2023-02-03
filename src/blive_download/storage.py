import os
import shutil
from time import sleep
import datetime
import os
from typing import Set
from ..model.VideoDB import VideoManager
from ..model.db import Video_DB

def _remove(file_path):
    if os.path.exists(file_path):
        os.remove(file_path)
        print("================================")
        print(datetime.datetime.now())
        print("File {} deleted".format(file_path))
    else:
        print("The file {} does not exist".format(file_path))


def residual(p):
    usage = shutil.disk_usage(p)
    return usage.used/usage.total

class StorageManager():
    DISK_USAGE_THRESHOLD = 0.8
    RELEASING_SIZE = 100*1024*1024*1024

    def __init__(self, path, engine) -> None:
        self.path = path
        self.engine = engine
        self.video_manager = VideoManager(engine = self.engine)
        self.modified_videos : Set[Video_DB]= set()
        self.deleted_size = 0
    

    def delete_video(self, video: Video_DB):
        _remove(video.videoname)
        _remove(video.subtitle_file)
        video.is_stored = False # type: ignore
        self.modified_videos.add(video)
        self.deleted_size += video.size

    def loop(self):
        print("Start Storage Management Loop")
        while True:
            self.modified_videos = set()
            self.deleted_size = 0
            print("===========StorageManager==========")
            print(datetime.datetime.now())
            print("Check Stored video files",flush=True)
            videos = self.video_manager.get_stored_videos()
            for v in videos:
                #Check is the file has been deleted or not
                if not os.path.exists(v.videoname):  
                    print("{} is missing on the disk".format(v.videoname))
                    v.is_stored = False 
                    self.modified_videos.add(v)
                    continue
                
                if residual(self.path) > self.DISK_USAGE_THRESHOLD:   #Add other judgement in the future 
                    # Check whether delete the video or not
                    if v.deletion_type == 0:
                        self.delete_video(v)
                    elif v.deletion_type == 1:
                        continue
                    elif v.deletion_type == 2:
                        if v.server_name:
                            self.delete_video(v)
                    
                    if self.deleted_size > self.RELEASING_SIZE:
                        break
            self.video_manager.update_videos(self.modified_videos)

            sleep(1800)
    



