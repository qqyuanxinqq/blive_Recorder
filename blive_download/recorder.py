import urllib
import time,datetime
import os
import json
from threading import Thread
import sys
# import subprocess
from typing import Tuple
import logging

from filelock import FileLock

from .api import is_live,get_stream_url,ws_open_msg,room_id
from .ws import danmu_ws
from .flvmeta import flvmeta_update

from .utils import configCheck
from .utils import Myproc
        
# from blive_upload import upload
#This absolute path import requires root directory have "blive_upload" folder

class Recorder():
    def __init__(self, up_name, upload_func =None):
        os.environ['TZ'] = 'Asia/Shanghai'
        if os.name != 'nt':
            time.tzset()
        self.up_name = up_name
        # self._room_id = int()
        # self._div_size_gb = int()
        # self._flvtag_update = 0  #Whether apply flvmeta to update flv tags, default 0
        # self._upload = 0    #Whether upload enabled, default not
        # self._path = ""
        self.upload_func = upload_func
                
        default_conf = configCheck()["_default"]
        self._room_id = default_conf["_room_id"]
        self._div_size_gb = default_conf["_div_size_gb"]
        self._flvtag_update = default_conf["_flvtag_update"]
        self._upload = default_conf["_upload"]
        self._path = default_conf["_path"]
        
        conf = configCheck(up_name = up_name)[self.up_name]
        for key in conf:
            setattr(self, key, conf[key])

        self.live_dir = os.path.join(self._path, up_name)
        self.div_size = round(eval("1024*1024*1024*" + self._div_size_gb))
        self._room_id = room_id(self._room_id)
        
        if self._upload == 1:
            #username/password or token file needed
            print("自动上传已启用")
        else:
            print("自动上传未启用")
        sys.stdout.flush()

        self.live_status = False
        print("[%s]Recorder loaded"%self.up_name,datetime.datetime.now(), flush=True)

    def check_live_status(self):
        try:
            self.live_status = is_live(self._room_id)
        except Exception as e:
            logging.exception(e)

        return self.live_status

    def get_stream_url(self):
        try:
            real_url,headers = get_stream_url(self._room_id)
        except Exception as e:
            logging.exception(e)
            return None,None
        return real_url,headers
        
    def recording(self):
        try: 
            while 1:
                while not self.check_live_status():
                    print("[%s]未开播"%self._room_id,datetime.datetime.now(), flush=True)
                    time.sleep(35)

                #Information about this live
                self.live = self.Live(self.up_name,self.live_dir)
                threads = []
                try:
                    self.live.dump_record_info()
                    #Record this live
                    ws = self.ws_setup()
                    while self.check_live_status() == True:                   
                        real_url,headers = self.get_stream_url()
                        if real_url == None:
                            print("开播了但是没有源")
                            time.sleep(5)
                            continue

                        #Init upload process  
                        if self._upload == 1 and self.live.record_info['Uploading'] == 'No':
                            self.live.record_info['Uploading'] = 'Yes'
                            self.upload(self.live.record_info)

                        #New video starts
                        self.live.init_video()
                        ass_gen(self.live.curr_video.ass_name,"head.ass") 
                        
                        if not self.ws_thread.is_alive():
                            print("WS has been terminated somehow!!!!")
                            ws = self.ws_setup()

                        rtncode, recorded = record(real_url, self.live.curr_video.videoname, headers, self.div_size)
                        print("Total number of danmu so far is : ", self.live.num_danmu_total, datetime.datetime.now())

                        #Current video ends
                        if recorded:
                            #Modify recorded video and dump updated record_info
                            self.live.dump_record_info()
                            t_post_record = Thread(target=self.post_record, args=(self.live.curr_video.videoname, self.live.append_curr_video), name=self.live.curr_video.videoname)
                            t_post_record.start()
                            threads.append(t_post_record)
                        else:
                            print("record failed on {}".format(self.live.curr_video.videoname))

                    #When live ends
                    ws.close()
                except Exception as e:
                    logging.exception(e)
                while threads:
                    threads.pop().join()
                time.sleep(10)

                self.live.record_info['Status'] = "Done"
                self.live.dump_record_info()
                print("Live Done ",datetime.datetime.now(), flush = True)
        finally:
            print("Terminated Gracefully!")


    def post_record(self, filename, callback):
        if self._flvtag_update:
            print("==========Flvmeta============\n", filename, flush = True)
            rtn = flvmeta_update(filename)
            print("==========Flvmeta============\n", rtn, flush = True)
            
        callback(filename)
    
    def ws_setup(self):
        opening_msg = ws_open_msg(int(self._room_id))
        ws = danmu_ws(opening_msg, self.live)
        self.ws_thread = Thread(target=ws.run_forever)
        self.ws_thread.setDaemon(True)
        self.ws_thread.start()        
        return ws

    
    def upload(self, record_info):
        if self.upload_func:
            upload_log_dir = os.path.join(self.live_dir,"upload_log")
            os.makedirs(upload_log_dir, exist_ok = True)
            logfile = os.path.join(upload_log_dir , record_info.get('time') + '.log')

            #Uploading process runs at blive_upload directory
            # p = subprocess.Popen(['nohup python3 -u ./blive_upload/{}.py {} > {} 2>&1  & echo $! > {}'.format(\
            # self.up_name,record_info.get('filename'), logfile, logfile)],\
            # shell=True)
            p = Myproc(target = self.upload_func, args = (record_info.get('filename'),), name="[{}]Uploader".format(self.up_name))
            p.set_output(logfile)
            p.start()
            p.post_run()
            print("=============================")
            print("开始上传"+record_info.get('filename'))
            print("=============================")
        else:
            print("=============================")
            print("No upload function provided")
            print("=============================")

    class Live():
        video_info_dir = "video_list"
        timeFormat = "_%Y%m%d_%H-%M-%S"
    
        class Video():
            def __init__(self) -> None:
                #Actually initiate by Live.init_video()
                self.danmu_end_time = [datetime.timedelta(seconds=0)]
                self.timeFormat = ""
                self.time_create = datetime.datetime.now()
                self.up_name = ""
                self.live_dir = ""
                self.filename = ""
                self.videoname = ""
                self.ass_name = ""

            def get_ass_info(self):
                return self.ass_name,self.time_create
        
        def __init__(self,up_name,live_dir):
            self.up_name = up_name
            self.time_create = datetime.datetime.now()
            self.num_danmu_total = 0
            self.live_dir = live_dir
            self.curr_video = self.Video()
            self.init_video()
            self.record_info_dir = os.path.join(self.live_dir, self.video_info_dir)
            os.makedirs(self.record_info_dir , exist_ok = True)
            self.set_record_info()

        def init_video(self):
            video = self.curr_video
            video.timeFormat = self.timeFormat
            video.time_create = datetime.datetime.now()
            video.up_name = self.up_name
            video.live_dir = self.live_dir
            video.filename = os.path.join(self.live_dir, self.up_name + video.time_create.strftime(self.timeFormat))
            video.videoname = video.filename +".flv"
            video.ass_name = video.filename + ".ass"        
            video.danmu_end_time.clear()
            video.danmu_end_time.append(datetime.timedelta(seconds=0))           


        def set_record_info(self):
            now = self.time_create
            self.record_info = {'year':now.strftime("%Y"),
                'month':now.strftime("%m"),
                'day':now.strftime("%d"),
                'hour':now.strftime("%H"),
                'time_format':self.timeFormat,
                'time':now.strftime(self.timeFormat),
                #Absolute path for record info file
                'filename':os.path.abspath(os.path.join(self.record_info_dir, self.up_name+ now.strftime(self.timeFormat+".json"))),
                'videolist':[],
                'up_name': self.up_name,
                #Absolute path for video directory
                'directory': os.path.abspath(self.live_dir),
                'Status':"Living",
                'Uploading': "No"
                }
        def dump_record_info(self):
            filename = self.record_info['filename']
            with FileLock(filename+".lock"):
                with open(filename, 'w') as f:
                    json.dump(self.record_info, f, indent=4) 
        
        def append_curr_video(self, videoname):
            self.record_info['videolist'].append(os.path.basename(videoname))
            print("{} appended to record info".format(videoname))
            self.dump_record_info()


        def danmu_rate(self, duration):
            prev_num = self.num_danmu_total
            time.sleep(duration)
            curr_num = self.num_danmu_total
            return curr_num - prev_num

def ass_gen(ass_name, header):
    if os.path.exists(ass_name) == False:
        with open (header,"r",encoding='UTF-8') as head:
            ass_head=head.read()
        with open (ass_name,"x",encoding='UTF-8') as f_ass:
            f_ass.write(ass_head)  

def record(url, file_name,headers,divsize) -> Tuple[int,str]:
    if not url:
        return -1, ""
    res = None
    retry_num = 0
    r = urllib.request.Request(url,headers=headers)  # type: ignore
    # print(url)
    while retry_num <5 :
        try :
            # Must add timeout, otherwise program may get stuck at read(5), where fd=5 is socket.
            res = urllib.request.urlopen(r, timeout = 5)  # type: ignore
            break
        except Exception as e:
            logging.exception(e)
            print(retry_num,"=============================")
            print(e)
            print("=============================")
            retry_num +=1
            time.sleep(1)
    if not res:
        return -1, ""  
    
    with open(file_name, 'wb') as f:    
        print('starting download from:\n%s\nto:\n%s' % (url, file_name))
        size = 0
        # _buffer = res.read(1024 *256)
        n = 0
        now_1=datetime.datetime.now()
        while n < 5:
            try:
                _buffer = res.read(1024 * 32)
            except Exception as e:
                _buffer = b''
                logging.exception(e)
                print("=============================")
                print(e)
                print("=============================")
            
            if len(_buffer) == 0:
                print('==========Currently buffer empty!=={}========='.format(n))
                n+=1
                time.sleep(0.2)
                
            else:
                n = 0
                f.write(_buffer)
                size += len(_buffer)
                if now_1 + datetime.timedelta(seconds=1) < datetime.datetime.now() :
                    now_1=datetime.datetime.now()
                    print('{:<4.2f} MB downloaded'.format(size/1024/1024),datetime.datetime.now())
                #sys.stdout.flush()
                if size > divsize:
                    print("=============Maximum Size reached!==============")
                    break

    print("finnally")
    if res:
        res.close()
        print("res.close()")

    if os.path.isfile(file_name) and os.path.getsize(file_name) == 0:
        os.remove(file_name)
        print("os.remove({})".format(file_name))
        return -1, ""

    return 0, file_name




