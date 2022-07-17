import json
import logging
from typing import Any, Callable, Dict, List, Optional, Union
# from sqlite3 import Timestamp
import zlib
from threading import Thread
import time, datetime
import os
from collections import defaultdict

import websocket
from src.blive_download.api import get_ws_host, ws_key, ws_open_msg

from ..model.LiveDB import Live

from ..model import Video_DB
from ..model import DanmuManager

Handler = Callable[[Dict], None]


def get_json(recv):      
    """
    process the received bytes element, return json object
    """
    if len(recv)==16:
        return []
    #print(recv[0:15]) ################################
    try:
        return [json.loads(recv[16:])]
    except Exception:
        try:
            temp=zlib.decompress(recv[16:])
            return [json.loads(temp[16:])]
        except Exception:
            # print("need double zlib")
            try:
                temp=zlib.decompress(recv[16:])
                i=1
                rtn=[]
                while temp[16+i:].find(b'\x00{"cmd":')!=-1:
                    j=temp[16+i:].find(b'\x00{"cmd":')+1
                    rtn.append(json.loads(temp[16+i-1:16+i+j-16]))
                    i=i+j+1
                rtn.append(json.loads(temp[16+i-1:]))
                return rtn
            except Exception as e:
                logging.exception(e)
                print("ERROR")
                print (e)
                print(recv)
    return []

def ass_time(timedelta):    
    """input 'datetime.timedelta' object, return ass time formt in str"""
    h=(timedelta//datetime.timedelta(seconds=3600))%10
    m=(timedelta//datetime.timedelta(seconds=60))%60
    s=(timedelta//datetime.timedelta(seconds=1))%60
    sd=(timedelta//datetime.timedelta(microseconds=10**4))%100
    return "{}:{:0>2d}:{:0>2d}.{:0>2d}".format(h,m,s,sd)

class Ass_Generator():
    """
    Generate and write danmu to *.ass file
    Work for the whole Live instead of single video

    If curr_video attribute doesn't exist, it ignores the message.
    """
    ASS_DURATION = 10
    RES_X = 1280
    RES_Y = 720
    def __init__(self, live: Live) -> None:
        self.liveinfo = live
        self.timer = time.time()
        self.ass_line_list = []
        # self.previous_ass_name = ""
        
        # self.cur_video = live.curr_video

    @property
    def curr_video(self) -> Optional[Video_DB]:
        if not hasattr(self.liveinfo, 'curr_video'):
            return None

        if self.liveinfo.curr_video:
            return self.liveinfo.curr_video
        else:
            return None
    # @property
    # def __ass_file(self):
    #     return self.liveinfo.curr_video.ass_name
    # @property
    # def __video_file(self):
    #     return self.liveinfo.curr_video.videoname
    # @property
    # def __ass_starttime(self):
    #     return self.liveinfo.curr_video.time_create
    # @property
    # def __end_time_lst(self):
    #     return self.liveinfo.curr_video.danmu_end_time

    def danmu_handler(self,j):
        """
        Input json object, output string in ass format
        If curr_video attribute doesn't exist, it ignores the message.
        """
        if self.curr_video:
            ass_line = self._danmu_to_ass_line(j,self.curr_video.danmu_end_time,self.curr_video.time_create)
            self._ass_write(ass_line, self.curr_video)
    
    def SC_handler(self,j):
        """
        Input json object, output string in ass format
        If curr_video attribute doesn't exist, it ignores the message.
        """
        if self.curr_video:
            ass_line = self._SC_to_ass_line(j,self.curr_video.danmu_end_time,self.curr_video.time_create)
            self._ass_write(ass_line, self.curr_video)

    def _ass_write(self, ass_line, curr_video: Video_DB):
        self.ass_line_list.append(ass_line)
        current = time.time()
        if os.path.exists(curr_video.videoname) and current > self.timer+1:  # type: ignore
            if not os.path.exists(curr_video.subtitle_file):
                self.ass_gen(curr_video.subtitle_file)
            with open(curr_video.subtitle_file,"a",encoding='UTF-8') as f:
                for ass_line in self.ass_line_list:
                    f.write(ass_line)
            self.ass_line_list.clear()
            self.timer = current

    def _SC_to_ass_line(self, j, end_time_lst, starttime):
        danmu = "SC:"+j["data"]["message"]
        username = j["data"]["user_info"]["uname"]
        color_h= j["data"]["background_bottom_color"][1:7]          #RGB in Hexadecimal
        timestamp_start = j["data"]["start_time"]
        timestamp_end = j["data"]["end_time"]

        danmu_l=len(danmu)*25
        danmu_start = datetime.datetime.fromtimestamp(timestamp_start)-starttime
        danmu_end = datetime.datetime.fromtimestamp(timestamp_end)-starttime
        #Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
        #Moving danmu: \move(<Start_x1>,<Start_y1>,<End_x2>,<End_y2>)
        Y = 0
        for i in range(len(end_time_lst)+1):
            #print(i)
            if i == len(end_time_lst):
                Y=i*25
                end_time_lst.append(danmu_end + danmu_l/self.RES_X*self.ASS_DURATION*datetime.timedelta(seconds=1))
                break
            if (self.RES_X + danmu_l) / self.ASS_DURATION * ((end_time_lst[i] - danmu_start)/datetime.timedelta(seconds=1)) >  self.RES_X: 
                continue
            else:
                Y=i*25
                end_time_lst[i] = danmu_end + danmu_l/self.RES_X*self.ASS_DURATION*datetime.timedelta(seconds=1)
                break
        move = "\\pos({},{})".format(self.RES_X//2, Y)+"\\c&H{}".format(''.join([color_h[4:6],color_h[2:4],color_h[0:2]]))
        ass_line="Dialogue: 0,{},{},R2L,{},20,20,2,,{{ {} }}{} \n".format(ass_time(danmu_start), 
                                                        ass_time(danmu_end),
                                                        username,
                                                        move,
                                                        danmu)
        return ass_line

    def _danmu_to_ass_line(self, j, end_time_lst, starttime):
        """Input json object and parameters for single msg, output string in ass format"""
        danmu = j.get('info')[1]
        username = j.get('info')[2][1]
        color_d=j.get('info')[0][3] #RGB in decimal
        color_h="{:X}".format(color_d) #RGB in Hexadecimal
        danmu_start = datetime.datetime.fromtimestamp(j.get('info')[0][4]/1000)-starttime
        
        danmu_l=len(danmu)*25   #Size of each chinese character is 25, english character considered to be half, 1280 is the X size from the .ass file
        danmu_end = danmu_start + datetime.timedelta(seconds=self.ASS_DURATION)
        #Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
        #Moving danmu: \move(<Start_x1>,<Start_y1>,<End_x2>,<End_y2>)
        X1 = self.RES_X + danmu_l / 2
        X2 = 0 - danmu_l / 2
        Y = 0
        for i in range(len(end_time_lst)+1):
            #print(i)
            if i == len(end_time_lst):
                Y=i*25
                end_time_lst.append(danmu_end + danmu_l/self.RES_X*self.ASS_DURATION*datetime.timedelta(seconds=1))
                break
            if (self.RES_X + danmu_l) / self.ASS_DURATION * ((end_time_lst[i] - danmu_start)/datetime.timedelta(seconds=1)) <=  1280: 
                Y=i*25
                end_time_lst[i] = danmu_end + danmu_l/self.RES_X*self.ASS_DURATION*datetime.timedelta(seconds=1)
                break
        move = "\\move({},{},{},{})".format(X1, Y, X2, Y)+"\\c&H{}".format(''.join([color_h[4:6],color_h[2:4],color_h[0:2]]))
        ass_line="Dialogue: 0,{},{},R2L,{},20,20,2,,{{ {} }}{} \n".format(ass_time(danmu_start), 
                                                        ass_time(danmu_end),
                                                        username,
                                                        move,
                                                        danmu)
        return ass_line

    def ass_gen(self, ass_name):
        if os.path.exists(ass_name) == False:
            ass_head =f'''\
[Script Info]
Title: blive_Recorder danmu generator
ScriptType: v4.00+
Collisions: Normal
PlayResX: {self.RES_X}
PlayResY: {self.RES_Y}
Timer: 10.0000

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Fix,Microsoft YaHei UI,25,&H00FFFFFF,&H00FFFFFF,&H00000000,&H66000000,1,0,0,0,100,100,0,0,1,1,0,8,20,20,2,0
Style: R2L,Microsoft YaHei UI,25,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,1,0,0,0,100,100,0,0,1,1,0,8,20,20,2,0

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.08,0:00:10.08,R2L,,20,20,2,,{{\\pos({self.RES_X//2},0)}}Danmu Record Start
'''
            with open (ass_name,"x",encoding='UTF-8') as f_ass:
                f_ass.write(ass_head)  



def on_error(ws, error):
    print("Error handler=====",error)

def on_close(ws, close_status_code, close_msg):
    ws.alive = False
    print("### danmu websocket closed ###")
    # Because on_close was triggered, we know the opcode = 8
    if close_status_code or close_msg:
        print("close status code: " + str(close_status_code))
        print("close message: " + str(close_msg))


def on_open_gen(opening_msg):  #generating on_open function with differnt opening_msg
    def on_open(ws):
        opening=opening_msg
        ws.send(opening)
        ws.alive = True
        def sendheartbeat():
            time.sleep(1)
            print("Sending Heartbeat")
            heartbeat=b'\x00\x00\x00\x1f\x00\x10\x00\x01\x00\x00\x00\x02\x00\x00\x00\x01[object Object]'
            while ws.alive:
                ws.send(heartbeat)
                print("Heartbeat sent")
                time.sleep(30)
        ws.t_sendheartbeat=Thread(target=sendheartbeat,name="Heartbeat_Sending_Thread")
        ws.t_sendheartbeat.start()
    return on_open


class Message_Handler():
    def __init__(self) -> None:
        self.handlers: defaultdict[str, List[Handler]] = defaultdict(list)
        self.cmd_list = []
        self.global_handler = []

    def handle(self, j) -> None:
        '''Input json object, handle it using the corresponding handlers'''
        # if j.get('cmd') not in self.cmd_list:
        #     self.cmd_list.append(j.get('cmd'))
        #     print(j)
        for handler in self.global_handler:
            try:
                handler(j)
            except Exception as e:
                logging.exception(e)
        
        if j.get('cmd') in self.handlers:
            for handler in self.handlers[j.get('cmd')]:
                try:
                    handler(j)
                except Exception as e:
                    logging.exception(e)
        elif j.get('cmd') == None:
            print(j)

    def set_handler(self, message_type:str):
        """Decorator generator"""
        def one(handler: Handler):
            self.handlers[message_type].append(handler)
        def all(handler: Handler):
            self.global_handler.append(handler)
        if message_type == "ALL":
            return all
        else:
            return one

    def on_message(self):
        '''
        Generate on_message function
        '''
        def on_message(ws, message):
            if message==b'\x00\x00\x00\x1a\x00\x10\x00\x01\x00\x00\x00\x08\x00\x00\x00\x01{"code":0}':
                print("Connected")
                return
            elif len(message)==20:
                print("Heartbeat confirmed")
                return
            
            elif len(message)==35:  #HeartBeat responding message contains 人气值
                renqi = int.from_bytes(message[16:20], 'big')
                print("当前人气",renqi)
                print("Heartbeat confirmed")

            else:
                for j in get_json(message):
                    self.handle(j)
        if not self.handlers and not self.global_handler:
            return None
        else:
            return on_message



class Danmu_To_DB():   #modify this in the future
    def __init__(self, live: Live, engine:Any = None) -> None:
        self.live = live

        if engine is not None:
            self.engine = engine
        elif self.live.engine is not None:
            self.engine = self.live.engine
        else:
            raise Exception("No database engine provided")

        self.danmu_manager = DanmuManager(engine = self.engine)
        self.danmu_DB_list = []
        self.timer = time.time()
        #A large interval can avoid frequent writing
        #Which is necessary for SQLite that doesn't support concurrent writing
        self.DBconnection_interval = 30  

    def danmu_handler(self,j):
        danmu_DB = dict(
            live_id = self.live.live_db.live_id,
            video_basename = self.live.curr_video.video_basename if self.live.curr_video else None,
            content = None,
            start_time = None,
            uid = None,
            username = None,
            type = None,
            color = None,
            price = None,
        )
        
        if j.get('cmd') == 'DANMU_MSG':
            danmu_DB.update(dict(
                content = j.get('info')[1],
                start_time = j.get('info')[0][4]//1000,
                uid = j.get('info')[2][0],
                username = j.get('info')[2][1],
                type = j.get('cmd'),
                color = j.get('info')[0][3]
            ))
            self.write_to_DB(danmu_DB)
        elif j.get('cmd') == 'SUPER_CHAT_MESSAGE':
            danmu_DB.update(dict(
                content = j["data"]["message"],
                start_time = j["data"]["start_time"],
                uid = j["data"]["uid"],
                username = j["data"]["user_info"]["uname"],
                type = j.get('cmd'),
                price = j["data"]["price"]
            ))
            self.write_to_DB(danmu_DB)
        
    def write_to_DB(self, entry):
        self.danmu_DB_list.append(entry)
        current = time.time()
        if self.danmu_DB_list and current > self.timer + self.DBconnection_interval:
            self.danmu_manager.insert_danmu(self.danmu_DB_list)
            self.danmu_DB_list.clear()
            self.timer = time.time()


class Danmu_Counter():
    def __init__(self,live_info) -> None:
        self.live_info = live_info
    def count(self, j):
        self.live_info.num_danmu_total += 1
    
def generate_handler(live_info:Live) -> Message_Handler:
    message_handler = Message_Handler()

    ass_handler = Ass_Generator(live_info)
    message_handler.set_handler('DANMU_MSG')(ass_handler.danmu_handler)
    message_handler.set_handler('SUPER_CHAT_MESSAGE')(ass_handler.SC_handler)
    # message_handler.set_handler('DANMU_MSG')(Danmu_Counter(live_info).count)
    message_handler.set_handler('ALL')(Danmu_To_DB(live_info).danmu_handler)

    return message_handler

class WebSocketAppManager():
    def __init__(self, room_id) -> None:
        self.room_id = room_id
        self.handler: Message_Handler = Message_Handler()
        self.maintain_ws = False
        self.ws: Optional[websocket.WebSocketApp]= None
        self.ws_thread: Optional[Thread] = None
        self.ws_loop_thread: Optional[Thread] = None

    def set_handler(self, message_handler:Message_Handler):
        self.handler = message_handler

    def init_ws(self):
        opening_msg =ws_open_msg(self.room_id)
        ws_host = get_ws_host(int(self.room_id))
        self.ws = websocket.WebSocketApp(f"wss://{ws_host}/sub",
                                on_message = self.handler.on_message(),
                                on_error=on_error,
                                on_close=on_close,
                                on_open = on_open_gen(opening_msg)
                                )
        return self.ws

    def run_ws_blocking(self):
        '''
        websocket.WebSocketApp.run_forever()
        Blocking until WebSocketApp terminated, e.g. by calling self.ws.close().
        '''
        if not self.ws:
            self.init_ws()
        if self.ws:
            self.ws.run_forever()

    def run_ws_thread(self):
        '''
        Run websocket.WebSocketApp.run_forever in a thread.
        Thread will terminated when WebSocketApp terminated, e.g. by calling self.ws.close().
        '''
        if not self.ws:
            self.init_ws()
        if self.ws:
            self.ws_thread = Thread(target=self.ws.run_forever)
            self.ws_thread.daemon = True
            self.ws_thread.start()        
            return self.ws_thread

    def run_ws_recon_blocking(self):
        '''
        Loop for restarting ws if terminated by errors. 
        It will stop and terminate the current WS thread for self.maintain_ws as False.
        '''
        self.maintain_ws = True
        while self.maintain_ws:
            if not self.ws_thread:
                print("Start WS!")
                self.init_ws()
                self.run_ws_thread()   
            elif not self.ws_thread.is_alive():
                print("WS has been terminated somehow! Restart WS!")
                self.init_ws()
                self.run_ws_thread()
            time.sleep(1)
        if self.ws:
            self.ws.close()

    def run_ws_recon_thread(self):
        '''
        Run websocket.WebSocketApp.run_ws_recon_blocking in a thread.
        Thread will terminated when self.maintain_ws set as False
        '''

        self.ws_loop_thread = Thread(target=self.run_ws_recon_blocking)
        self.ws_loop_thread.daemon = True
        self.ws_loop_thread.start()        
        return self.ws_loop_thread