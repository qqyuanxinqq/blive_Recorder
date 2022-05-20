import os
import json

CONFIG_PATH = os.path.join("config","config.json")

def configCheck(configpath = CONFIG_PATH, up_name="_default"):
    if os.path.exists(configpath) == False:
        print("请确认配置文件{}存在，并填写相关配置内容".format(configpath))
        raise Exception("config file error!")
    conf = json.load(open(configpath))
    if conf.get(up_name,0) == 0:
        print("请确认该配置文件中存在与%s相匹配的信息"%up_name)
        raise Exception("config file error!")
    if conf[up_name].get("_name",0) != up_name:
        print("请确认该配置文件中_name项的信息与%s相匹配"%up_name)
        raise Exception("config file error!")
    if not conf["_default"].get("Database",0):
        print("请确认已提供database的目录")
        raise Exception("config file error!")
    return conf