import time
import subprocess

def test_cmd(cmd):
    start = time.time()
    subprocess.run(cmd, shell=True, stdout=subprocess.DEVNULL)
    return time.time() - start

print(test_cmd("python3 hbctool/test.py"))
