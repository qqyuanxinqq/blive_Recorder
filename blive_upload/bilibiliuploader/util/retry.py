from time import sleep

class Retry:
    def __init__(self, max_retry, check_func = lambda x: x):
        '''
        return (False,None) or (True,return_value)
        '''
        self.max_retry = max_retry
        # self.success_return_value = success_return_value
        self.check_func = check_func

    def run(self, func, *args, **kwargs):
        status = (False, None)
        for i in range(0, self.max_retry):
            print("Trials {}/{} :".format(i+1,self.max_retry))
            try:
                return_value = func(*args, **kwargs)
                if self.check_func(return_value):
                    status = (True,return_value)
                    break
            except Exception as e:
                # return_value = not self.success_return_value
                print("Exceptions in trial {}/{} :".format(i+1,self.max_retry), e)
                sleep(120)

        return status
