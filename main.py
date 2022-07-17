import sys
from src.blive_download import Recorder, App
from src.blive_upload import configured_upload


if __name__ == '__main__':
    CONFIG_PATH = "config.json"
    if len(sys.argv) == 2:
        # Get up_name from prompt
        up_name = sys.argv[1]
        # Up_name should be matched up with configuration file (i.e. kaofish for ./config/kaofish.json)
        recorder = Recorder(up_name)
        recorder.init_from_json(CONFIG_PATH)
        recorder.run()
    elif len(sys.argv) == 1:
        app = App(CONFIG_PATH)
        app.run()




            
