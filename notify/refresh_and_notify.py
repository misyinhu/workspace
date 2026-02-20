#!/usr/bin/env python3
"""执行监控刷新并发送飞书通知"""

import sys
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import yaml
import requests
import json

from config import get_feishu_app_id, get_feishu_app_secret, get_feishu_chat_id, load_config, get

sys.path.insert(0, str(PROJECT_ROOT / "z120_monitor"))


def load_feishu_config():
    """从 settings.yaml 加载飞书配置"""
    load_config()
    return {
        "app_id": get_feishu_app_id(),
        "app_secret": get_feishu_app_secret(),
        "chat_id": get_feishu_chat_id(),
        "api_endpoint": get("feishu.api_endpoint", "https://open.feishu.cn/open-apis/im/v1/messages"),
        "auth_endpoint": get("feishu.auth_endpoint", "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"),
        "timeout": get("feishu.timeout", 30),
    }


def main():
    feishu_config = load_feishu_config()
    app_id = feishu_config.get("app_id")
    app_secret = feishu_config.get("app_secret")
    chat_id = feishu_config.get("chat_id")

    from z120_scheduler import Z120ScheduledMonitor
    from z120_cache import get_all_status, format_status_text
    import time

    Z120ScheduledMonitor()._run_once()
    time.sleep(2)

    data = get_all_status()
    if data:
        result = "✅ **监控数据已刷新**\n\n" + format_status_text()
    else:
        result = "❌ **监控刷新失败**，暂无数据"

    auth_url = feishu_config.get("auth_endpoint")
    msg_url = feishu_config.get("api_endpoint")

    auth_resp = requests.post(
        auth_url,
        json={"app_id": app_id, "app_secret": app_secret},
        timeout=10,
    )

    auth_resp = requests.post(
        auth_url,
        json={"app_id": app_id, "app_secret": app_secret},
        timeout=10,
    )
    token = auth_resp.json().get("tenant_access_token")

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    message = {
        "receive_id": chat_id,
        "msg_type": "text",
        "content": json.dumps({"text": result}),
    }

    resp = requests.post(
        msg_url,
        params={"receive_id_type": "chat_id"},
        json=message,
        headers=headers,
        timeout=10,
    )
    print("Status:", resp.status_code)
    print("Response:", resp.text[:200])


if __name__ == "__main__":
    main()
