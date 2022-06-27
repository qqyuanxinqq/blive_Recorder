import subprocess
import os.path
import logging

def flvmeta(input, options="", output = ""):
    '''
    ./flvmeta [options] [input] [output]
    Man page for flvmeta, https://flvmeta.com/flvmeta.1.html
    '''
    if not __file__:
        raise ImportError("__file__ not set")
    path = os.path.dirname(os.path.relpath(__file__))
    if not path:
        raise FileNotFoundError("Failed to find correct path for flvmeta")
    cmd = [os.path.join(path, "flvmeta")]
    for i in (*options.split(" "), input, output):
        if i:
            cmd.append(i)
    try:
        rtn = subprocess.run(cmd, capture_output=True)
        if rtn.returncode:
            return rtn.returncode,rtn.stderr.decode("utf-8")
        else:
            return rtn.returncode,rtn.stdout.decode("utf-8")
    except Exception as e:
        logging.exception(e)
        return -1,'Flvmeta binary error'

def flvmeta_update(input, options = "", output = ""):
    opt = "-U"
    if options:
        opt = opt + " " + options
    return flvmeta(input, opt, output)

def flvmeta_dump(input, options = ""):
    opt = "-D"
    if options:
        opt = opt + " " + options
    return flvmeta(input, opt)

def flvmeta_fulldump(input, options = ""):
    opt = "-F"
    if options:
        opt = opt + " " + options
    return flvmeta(input, opt)

def flvmeta_check(input, options = ""):
    opt = "-C"
    if options:
        opt = opt + " " + options
    return flvmeta(input, opt)
