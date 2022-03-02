import json
import websocket
import zlib
import time
from threading import Thread
import time,datetime
import os

def get_json(recv):      #process the received bytes element
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
                while temp[16+i:].find(b'{"cmd":')!=-1:
                    j=temp[16+i:].find(b'{"cmd":')
                    rtn.append(json.loads(temp[16+i-1:16+i+j-16]))
                    i=i+j+1
                rtn.append(json.loads(temp[16+i-1:]))
                return rtn
            except Exception as e:
                print("ERROR")
                print (e)
                print(recv)

def ass_time(timedelta):    #input 'datetime.timedelta' object, return ass time formt in str
    h=(timedelta//datetime.timedelta(seconds=3600))%10
    m=(timedelta//datetime.timedelta(seconds=60))%60
    s=(timedelta//datetime.timedelta(seconds=1))%60
    sd=(timedelta//datetime.timedelta(microseconds=10**4))%100
    return "{}:{:0>2d}:{:0>2d}.{:0>2d}".format(h,m,s,sd)


def danmu_to_ass(live_info):
    video_info = live_info.curr_video
    # end_time_lst = [datetime.timedelta(seconds=0)]  #(danmu_end-last_danmu_end)  speed() "Each line in the subtitle"
    end_time_lst = video_info.danmu_end_time
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
                #print(j)
                if j.get('cmd')=='DANMU_MSG':
                    danmu = j.get('info')[1]
                    username = j.get('info')[2][1]
                    color_d=j.get('info')[0][3] #RGB in decimal
                    color_h="{:X}".format(color_d) #RGB in Hexadecimal
                    #danmu_l=(len(danmu.encode('gbk')))*25/2     #Size of each chinese character is 25, english character considered to be half, 768 is the X size from the .ass file
                    danmu_l=len(danmu)*25
                    danmu_start = datetime.datetime.now()-video_info.time_create
                    danmu_end = danmu_start + datetime.timedelta(seconds=10)
                    #Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
                    #Moving danmu: \move(<Start_x1>,<Start_y1>,<End_x2>,<End_y2>)
                    X1 = 768 + danmu_l / 2
                    X2 = 0 - danmu_l / 2
                    for i in range(len(end_time_lst)+1):
                        #print(i)
                        if i == len(end_time_lst):
                            Y=i*25
                            end_time_lst.append(danmu_end)
                            break
                        if (768 + danmu_l) / 10 * ((end_time_lst[i] - danmu_start)/datetime.timedelta(seconds=1)) >  768: 
                            continue
                        else:
                            Y=i*25
                            end_time_lst[i] = danmu_end
                            break
                    move = "\\move({},{},{},{})".format(X1, Y, X2, Y)+"\\c&H{}".format(''.join([color_h[4:6],color_h[2:4],color_h[0:2]]))
                    ass_line="Dialogue: 0,{},{},R2L,{},20,20,2,,{{ {} }}{} \n".format(ass_time(danmu_start), 
                                                                    ass_time(danmu_end),
                                                                    username,
                                                                    move,
                                                                    danmu)
                    live_info.num_danmu_total += 1
                    # print(danmu)
                    # print(video_info.ass_name)
                    if os.path.exists(video_info.ass_name) == True:
                        with open(video_info.ass_name,"a",encoding='UTF-8') as f:
                            f.write(ass_line)
    return on_message


def on_error(ws, error):
    print(error)

def on_close(ws):
    ws.alive = False
    print("### danmu websocket closed ###")


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

def danmu_ws(opening,live_info):
    ws = websocket.WebSocketApp("wss://tx-live-dmcmt-sv-01.chat.bilibili.com/sub",
                              on_message = danmu_to_ass(live_info),
                               on_error=on_error,
                               on_close=on_close)
    ws.on_open = on_open_gen(opening)
    return ws
