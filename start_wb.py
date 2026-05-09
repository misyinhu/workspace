import subprocess
import sys
import os

env = os.environ.copy()
env["HTTP_PROXY"] = "http://127.0.0.1:7890"
env["HTTPS_PROXY"] = "http://127.0.0.1:7890"

p = subprocess.Popen(
    [
        r"C:\Users\wang\AppData\Local\Programs\Python\Python312\python.exe",
        r"C:\projects\trading\notify\webhook_bridge.py",
    ],
    cwd=r"C:\projects\trading\notify",
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
    env=env,
)
print(f"Started PID: {p.pid}")
