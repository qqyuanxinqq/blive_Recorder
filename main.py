import sys
from record import Recorder

if __name__ == '__main__':
    # Get up_name from prompt
    up_name = sys.argv[1]
    # Up_name should be matched up with configuration file (i.e. kaofish for ./config/kaofish.json)
    recorder = Recorder(up_name)
    recorder.recording()




            
