import os

def remove(path):
    if os.path.exists(path):
        os.remove(path)
    else:
        print("The file {} does not exist".format(path))

# trash recycle 