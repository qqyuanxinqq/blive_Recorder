from time import sleep
import datetime
import logging
from typing import Any, Tuple

class Retry:
    def __init__(self, max_retry: int, check_func = lambda r: r, interval: int = 120, default = None):
        '''
        return (False,None) or (True,return_value)
        '''
        self.max_retry = max_retry
        # self.success_return_value = success_return_value
        self.check_func = check_func
        self.interval = interval
        self.default = default

    def run(self, func, *args, **kwargs) -> Tuple[bool, Any]:
        status = (False, self.default)
        for i in range(0, self.max_retry):
            # print("Trials {}/{} :".format(i+1,self.max_retry))
            try:
                return_value = func(*args, **kwargs)
                if self.check_func(return_value):
                    status = (True,return_value)
                    break
            except Exception as e:
                print("================================")
                print(datetime.datetime.now())
                print("Exceptions in trial {}/{} :".format(i+1,self.max_retry), e, flush=True)
                # logging.exception(e)
                sleep(self.interval)

        return status

    def decorator(self, func):
        def _(*args, **kwargs):
            return self.run(func, *args, **kwargs)[1]
        return _


