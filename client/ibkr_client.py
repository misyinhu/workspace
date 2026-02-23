#!/usr/bin/env python3
"""客户端ID管理工具"""

import os
import sys
import psutil
import time

# 添加配置路径
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import load_config, get_ibkr_host, get_ibkr_port

# 加载配置
load_config()

IBKR_HOST = get_ibkr_host()
IBKR_PORT = get_ibkr_port()


def is_web_environment():
    """检测是否为Web环境"""
    env = os.environ

    # 允许手动指定环境类型（优先级最高）
    if "IB_ENV_TYPE" in env:
        env_type = env["IB_ENV_TYPE"].lower()
        if env_type == "web":
            return True
        elif env_type == "terminal":
            return False

    # SSH连接明确是Terminal环境
    if env.get("SSH_CLIENT") or env.get("SSH_TTY"):
        return False

    # 检测Web特定环境变量
    web_env_vars = ["OPENCODE_SESSION", "CLAUDE_WEB_SESSION", "WEB_OPENCODE_ENV"]
    if any(var in env for var in web_env_vars):
        return True

    try:
        # 获取进程树信息
        current_pid = os.getpid()
        parent = psutil.Process(current_pid)
        grandparent = psutil.Process(parent.ppid())
        great_grandparent = psutil.Process(grandparent.ppid())

        # 只检测进程名称，不检测命令行参数（避免误匹配注释）
        parent_name = parent.name().lower()
        grandparent_name = grandparent.name().lower()
        great_grandparent_name = great_grandparent.name().lower()

        # Web环境特征进程
        web_processes = [
            "node",
            "chrome",
            "firefox",
            "electron",
            "safari",
            "opencode",
            "claude",
        ]

        # 检查父进程、祖父进程、曾祖父进程
        for proc_name in [parent_name, grandparent_name, great_grandparent_name]:
            if any(web_proc in proc_name for web_proc in web_processes):
                return True

        return False
    except:
        return False

    # 检测Web特定环境变量
    web_env_vars = ["OPENCODE_SESSION", "CLAUDE_WEB_SESSION", "WEB_OPENCODE_ENV"]
    if any(var in env for var in web_env_vars):
        return True

    try:
        # 获取进程树信息
        current_pid = os.getpid()
        parent = psutil.Process(current_pid)
        grandparent = psutil.Process(parent.ppid())
        great_grandparent = psutil.Process(grandparent.ppid())

        # 只检测进程名称，不检测命令行参数（避免误匹配注释）
        parent_name = parent.name().lower()
        grandparent_name = grandparent.name().lower()
        great_grandparent_name = great_grandparent.name().lower()

        # Web环境特征进程
        web_processes = [
            "node",
            "chrome",
            "firefox",
            "electron",
            "safari",
            "opencode",
            "claude",
        ]

        # 检查父进程、祖父进程、曾祖父进程
        for proc_name in [parent_name, grandparent_name, great_grandparent_name]:
            if any(web_proc in proc_name for web_proc in web_processes):
                return True

        return False
    except:
        return False


def get_client_id():
    """获取clientId
    - Web环境: 返回 0
    - Z120环境: 返回 1
    - 其他: 动态分配 2-10
    """
    # 检测 Z120 环境（通过环境变量或进程名）
    if os.environ.get("IB_ENV_TYPE") == "z120":
        return 1
    
    # 检测是否是 z120_scheduler.py 进程
    try:
        current_pid = os.getpid()
        parent = psutil.Process(current_pid)
        # 检查进程名或命令行是否包含 z120
        cmdline = " ".join(parent.cmdline() or [])
        if "z120_scheduler" in cmdline or "z120_monitor" in cmdline:
            return 1
    except:
        pass
    
    # Web 环境固定用 0
    if is_web_environment():
        return 0

    # 动态分配 2-9
    for client_id in range(2, 10):
        if is_client_id_available(client_id):
            return client_id
    # 都不可用，强制 kill clientId=2 然后返回 2
    print("⚠️ 所有 clientId 不可用，强制释放 clientId=2")
    kill_process_using_client_id(2)
    return 2


def is_client_id_available(client_id):
    """检查clientId是否可用（真正尝试连接）"""
    try:
        from ib_insync import IB

        ib_test = IB()
        ib_test.connect(IBKR_HOST, IBKR_PORT, clientId=client_id, timeout=5)
        ib_test.disconnect()
        return True
    except Exception as e:
        return False


def kill_process_using_client_id(target_client_id):
    """终止使用指定clientId的进程"""
    if target_client_id == 1 or target_client_id == 0:
        return  # 永不kill scheduler 或 web client

    for proc in psutil.process_iter(["pid", "cmdline"]):
        try:
            cmdline = " ".join(proc.info["cmdline"] or [])
            if f"clientId={target_client_id}" in cmdline:
                print(
                    f"🔪 终止进程PID {proc.info['pid']} (clientId={target_client_id})"
                )
                proc.terminate()
                time.sleep(1)
                if proc.is_running():
                    proc.kill()
                return True
        except:
            continue
    return False
