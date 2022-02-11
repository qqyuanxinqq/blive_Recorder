from time import sleep

class Retry:
    def __init__(self, max_retry, success_return_value):
        self.max_retry = max_retry
        self.success_return_value = success_return_value

    def run(self, func, *args, **kwargs):
        status = False
        for i in range(0, self.max_retry):
            print("Trials {}/{} :".format(i+1,self.max_retry))
            try:
                return_value = func(*args, **kwargs)
            except Exception as e:
                return_value = not self.success_return_value
                print("Exceptions in trial {}/{} :".format(i+1,self.max_retry), e)
                sleep(120)
            if return_value == self.success_return_value:
                status = True
                break
        return status
