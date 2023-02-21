def configCheck(configpath:str, up_name:str="_default", list_all = False) -> dict:
    '''
    Check configuration in configuration json file. 
    If up_name not provided, it will check "_default" as default setting.
    If list_all set True, return the whole json file.
    '''
    # if os.path.exists(configpath) == False:
    #     print("请确认配置文件{}存在，并填写相关配置内容".format(configpath))
    #     raise Exception("config file error!")
    
    if configpath.split(".")[-1] == "json":
        import json
        conf = json.load(open(configpath))
    elif configpath.split(".")[-1] == "yaml":
        import yaml
        with open(configpath, "r") as f:
            conf = yaml.safe_load(f)
    else:
        raise Exception("Invalid file Extension, please provide *.yaml or *.json file")
    
    if list_all:
        return conf
    elif conf.get(up_name,0) == 0:
        raise Exception("请确认该配置文件中存在与%s相匹配的信息"%up_name)
    elif conf[up_name].get("name",0) != up_name:
        raise Exception("请确认该配置文件中_name项的信息与%s相匹配"%up_name)
    return conf[up_name]

def set_config(obj, dict):
    pass


# def _merge(src, dst):
#     for k, v in src.items():
#         if k in dst:
#             if isinstance(v, dict):
#                 _merge(src[k], dst[k])
#         else:
#             dst[k] = v


# def load_default_config():
#     config = DEFAULTS
#     return config


# def _update_config(config):
#     config["model"].update(config["input"])
#     config["model"]["train_cfg"] = config["train_cfg"]
#     config["model"]["test_cfg"] = config["test_cfg"]
#     return config


# def load_config(config_file, defaults=DEFAULTS):
#     with open(config_file, "r") as fd:
#         config = yaml.load(fd, Loader=yaml.FullLoader)
#     _merge(defaults, config)
#     config = _update_config(config)
#     return config


    
