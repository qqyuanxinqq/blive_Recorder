from flvmeta import flvmeta,flvmeta_update

def test():
    filename = "/home/xyl/f/blive_Rcorder/Videos/kaofish/kaofish_202202 12_02-42-27.flv"
    a,b = flvmeta_update(filename, "", output="test.flv")
    print(a)
    print(b)

test()