import json
import logging
# from sqlite3 import Timestamp
import zlib
from threading import Thread
import time, datetime
import os
from collections import defaultdict

import websocket

from .model import DanmuManager

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

ASS_DURATION = 10
class Ass_Generator():
    """
    Generate and write danmu to *.ass file
    Work for the whole Live instead of single video

    If curr_video attribute doesn't exist, it ignores the message.
    """
    def __init__(self, live) -> None:
        self.liveinfo = live
        self.timer = time.time()
        self.ass_line_list = []
        # self.previous_ass_name = ""
        
        # self.cur_video = live.curr_video

    @property
    def curr_video(self):
        if not hasattr(self.liveinfo, 'curr_video'):
            return False

        if self.liveinfo.curr_video:
            return True
        else:
            return False

    @property
    def __ass_file(self):
        return self.liveinfo.curr_video.ass_name
    @property
    def __ass_starttime(self):
        return self.liveinfo.curr_video.time_create
    @property
    def __end_time_lst(self):
        return self.liveinfo.curr_video.danmu_end_time

    def danmu_handler(self,j):
        """
        Input json object, output string in ass format
        If curr_video attribute doesn't exist, it ignores the message.
        """
        if self.curr_video:
            ass_line = self._danmu_to_ass_line(j,self.__end_time_lst,self.__ass_starttime)
            self._ass_write(ass_line)
    
    def SC_handler(self,j):
        """
        Input json object, output string in ass format
        If curr_video attribute doesn't exist, it ignores the message.
        """
        if self.curr_video:
            ass_line = self._SC_to_ass_line(j,self.__end_time_lst,self.__ass_starttime)
            self._ass_write(ass_line)

    def _ass_write(self, ass_line):
        self.ass_line_list.append(ass_line)
        current = time.time()
        if os.path.exists(self.__ass_file) and current > self.timer+1:
            with open(self.__ass_file,"a",encoding='UTF-8') as f:
                for ass_line in self.ass_line_list:
                    f.write(ass_line)
            self.ass_line_list.clear()
            self.timer = current

    @staticmethod
    def _SC_to_ass_line(j, end_time_lst, starttime):
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
        # X1 = 768 + danmu_l / 2
        # X2 = 0 - danmu_l / 2
        for i in range(len(end_time_lst)+1):
            #print(i)
            if i == len(end_time_lst):
                Y=i*25
                end_time_lst.append(danmu_end + danmu_l/768*ASS_DURATION*datetime.timedelta(seconds=1))
                break
            if (768 + danmu_l) / ASS_DURATION * ((end_time_lst[i] - danmu_start)/datetime.timedelta(seconds=1)) >  768: 
                continue
            else:
                Y=i*25
                end_time_lst[i] = danmu_end + danmu_l/768*ASS_DURATION*datetime.timedelta(seconds=1)
                break
        move = "\\pos({},{})".format(384, Y)+"\\c&H{}".format(''.join([color_h[4:6],color_h[2:4],color_h[0:2]]))
        ass_line="Dialogue: 0,{},{},R2L,{},20,20,2,,{{ {} }}{} \n".format(ass_time(danmu_start), 
                                                        ass_time(danmu_end),
                                                        username,
                                                        move,
                                                        danmu)
        return ass_line
    @staticmethod
    def _danmu_to_ass_line(j, end_time_lst, starttime):
        """Input json object and parameters for single msg, output string in ass format"""
        danmu = j.get('info')[1]
        username = j.get('info')[2][1]
        color_d=j.get('info')[0][3] #RGB in decimal
        color_h="{:X}".format(color_d) #RGB in Hexadecimal
        danmu_start = datetime.datetime.fromtimestamp(j.get('info')[0][4]/1000)-starttime
        
        danmu_l=len(danmu)*25   #Size of each chinese character is 25, english character considered to be half, 768 is the X size from the .ass file
        danmu_end = danmu_start + datetime.timedelta(seconds=ASS_DURATION)
        #Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
        #Moving danmu: \move(<Start_x1>,<Start_y1>,<End_x2>,<End_y2>)
        X1 = 768 + danmu_l / 2
        X2 = 0 - danmu_l / 2
        Y = 0
        for i in range(len(end_time_lst)+1):
            #print(i)
            if i == len(end_time_lst):
                Y=i*25
                end_time_lst.append(danmu_end + danmu_l/768*ASS_DURATION*datetime.timedelta(seconds=1))
                break
            if (768 + danmu_l) / ASS_DURATION * ((end_time_lst[i] - danmu_start)/datetime.timedelta(seconds=1)) <=  768: 
                Y=i*25
                end_time_lst[i] = danmu_end + danmu_l/768*ASS_DURATION*datetime.timedelta(seconds=1)
                break
        move = "\\move({},{},{},{})".format(X1, Y, X2, Y)+"\\c&H{}".format(''.join([color_h[4:6],color_h[2:4],color_h[0:2]]))
        ass_line="Dialogue: 0,{},{},R2L,{},20,20,2,,{{ {} }}{} \n".format(ass_time(danmu_start), 
                                                        ass_time(danmu_end),
                                                        username,
                                                        move,
                                                        danmu)
        return ass_line


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
        self.handlers = defaultdict(list)
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

    def set_handler(self, message_type):
        """Decorator generator"""
        def one(handler):
            self.handlers[message_type].append(handler)
        def all(handler):
            self.global_handler.append(handler)
        if message_type == "ALL":
            return all
        else:
            return one



def on_message_gen(message_handler):
    # video_info = live_info.curr_video
    # end_time_lst = [datetime.timedelta(seconds=0)]  #(danmu_end-last_danmu_end)  speed() "Each line in the subtitle"
    # end_time_lst = video_info.danmu_end_time
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
                message_handler.handle(j)
                        
    return on_message



class Danmu_To_DB():
    def __init__(self, live, engine) -> None:
        self.live = live
        self.engine = engine
        self.danmu_manager = DanmuManager(self.engine)
        self.danmu_DB_list = []
        self.timer = time.time()
        #A large interval can avoid frequent writing
        #Which is necessary for SQLite that doesn't support concurrent writing
        self.DBconnection_interval = 30  

    def danmu_handler(self,j):
        danmu_DB = dict(
            live_id = self.live.live_DB.live_id,
            video_id = self.live.curr_video.video_id,
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
                live_id = self.live.live_DB.live_id,
                video_id = self.live.curr_video.video_id,
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
                live_id = self.live.live_DB.live_id,
                video_id = self.live.curr_video.video_id,
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
    
def danmu_ws(opening,live_info, engine):
    message_handler = Message_Handler()

    ass_handler = Ass_Generator(live_info)
    message_handler.set_handler('DANMU_MSG')(ass_handler.danmu_handler)
    message_handler.set_handler('SUPER_CHAT_MESSAGE')(ass_handler.SC_handler)
    
    message_handler.set_handler('DANMU_MSG')(Danmu_Counter(live_info).count)

    message_handler.set_handler('ALL')(Danmu_To_DB(live_info, engine).danmu_handler)
   
    ws = websocket.WebSocketApp("wss://broadcastlv.chat.bilibili.com/sub",
                              on_message = on_message_gen(message_handler),
                               on_error=on_error,
                               on_close=on_close)
    ws.on_open = on_open_gen(opening)  # type: ignore
    return ws
