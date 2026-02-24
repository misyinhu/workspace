#!/usr/bin/env python3
"""Z120 状态缓存管理 - 支持多标的，保存历史价差数据"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

CACHE_DIR = Path(__file__).parent / ".." / "data"
CACHE_DIR.mkdir(exist_ok=True)
CACHE_FILE = CACHE_DIR / "z120_status.json"
MAX_HISTORY_DAYS = 10


def save_status(
    pair_name: str,
    zscore: Optional[float],
    spread: float,
    mean: float,
    std: float,
    threshold: float = 0,
    timestamp: Optional[datetime] = None,
):
    """保存单个标的的状态到缓存，追加到历史记录

    Args:
        timestamp: 可选的自定义时间戳，用于历史重建。如果为None则使用当前时间。
    """
    try:
        data = {}
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE) as f:
                data = json.load(f)

        now = timestamp or datetime.now()
        now_iso = now.isoformat()
        now_str = now.strftime("%Y-%m-%d %H:%M:%S")

        # 初始化或获取历史记录
        if pair_name not in data:
            data[pair_name] = {"history": []}

        # 如果不是自定义时间戳（实时保存），则清理10天前的旧数据
        if timestamp is None:
            cutoff = (datetime.now() - timedelta(days=MAX_HISTORY_DAYS)).isoformat()
            data[pair_name]["history"] = [
                h for h in data[pair_name]["history"] if h.get("timestamp", "") > cutoff
            ]

        # 追加新记录
        data[pair_name]["history"].append(
            {
                "timestamp": now_iso,
                "spread": spread,
            }
        )

        # 更新当前状态（始终使用最新数据）
        if timestamp is None or not data[pair_name].get("zscore"):
            data[pair_name].update(
                {
                    "zscore": zscore,
                    "spread": spread,
                    "mean": mean,
                    "std": std,
                    "threshold": threshold,
                    "timestamp": now_iso,
                    "updated_at": now_str,
                }
            )

        # 原子写入：先写临时文件，再重命名
        temp_file = CACHE_FILE.with_suffix('.tmp')
        try:
            with open(temp_file, "w") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            os.replace(temp_file, CACHE_FILE)
        except Exception:
            if os.path.exists(temp_file):
                os.remove(temp_file)
            raise
        return True
    except Exception as e:
        print(f"❌ 保存缓存失败 ({pair_name}): {e}")
        return False


def get_spread_change(pair_name: str, days: int = 7) -> dict:
    """
    获取价差变化量
    返回: {"current": xxx, "past": xxx, "change": xxx, "change_pct": xxx}
    """
    try:
        data = {}
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE) as f:
                data = json.load(f)

        history = data.get(pair_name, {}).get("history", [])
        if not history:
            return {}

        now = datetime.now()
        cutoff = (now - timedelta(days=days)).isoformat()

        # 找7天前的记录
        past_record = None
        for h in reversed(history):
            if h.get("timestamp", "") <= cutoff:
                past_record = h
                break

        # 当前记录（最新的）
        current_record = history[-1] if history else None

        if not current_record or not past_record:
            return {}

        current_spread = current_record.get("spread", 0)
        past_spread = past_record.get("spread", 0)
        change = current_spread - past_spread

        return {
            "current": current_spread,
            "past": past_spread,
            "change": change,
            "change_pct": (change / past_spread * 100) if past_spread != 0 else 0,
            "days": days,
        }
    except Exception as e:
        print(f"❌ 获取价差变化失败 ({pair_name}): {e}")
        return {}


def get_cached_status(pair_name: str = None):
    """读取缓存状态"""
    try:
        if not os.path.exists(CACHE_FILE):
            return None
        with open(CACHE_FILE) as f:
            data = json.load(f)

        if pair_name:
            return data.get(pair_name)
        return data
    except Exception as e:
        print(f"❌ 读取缓存失败: {e}")
        return None


def get_cached_spread_history(pair_name: str, days: int = 7) -> list:
    """按时间范围获取历史价差数据，不管有多少条"""
    try:
        if not os.path.exists(CACHE_FILE):
            return None

        with open(CACHE_FILE) as f:
            data = json.load(f)

        history = data.get(pair_name, {}).get("history", [])
        if not history:
            return None

        now = datetime.now()
        cutoff = (now - timedelta(days=days)).isoformat()

        # 按时间范围筛选（history是最旧在前）
        filtered = [
            h.get("spread", 0) for h in history if h.get("timestamp", "") > cutoff
        ]
        return filtered if filtered else None
    except Exception as e:
        print(f"❌ 获取历史价差失败 ({pair_name}): {e}")
        return None


def get_all_status():
    """获取所有标的的缓存状态"""
    try:
        if not os.path.exists(CACHE_FILE):
            return {}
        with open(CACHE_FILE) as f:
            return json.load(f)
    except:
        return {}


def clear_cache():
    """清除缓存"""
    try:
        if os.path.exists(CACHE_FILE):
            os.remove(CACHE_FILE)
            return True
    except:
        pass
    return False


def format_status_text(pair_name: str = None):
    """获取格式化的状态文本"""
    if pair_name:
        cached = get_cached_status(pair_name)
        if cached:
            zscore = cached.get("zscore", "N/A")
            spread = cached.get("spread", "N/A")
            threshold = cached.get("threshold", 0)
            updated = cached.get("updated_at", "未知")

            change_info = get_spread_change(pair_name, days=7)
            change = change_info.get("change", 0) if change_info else 0

            status = f"**{pair_name}:**\n"
            status += (
                f"  Z120: {zscore:.2f}"
                if isinstance(zscore, (int, float))
                else f"  Z120: {zscore}\n"
            )
            status += (
                f"  价差: {spread:.2f}"
                if isinstance(spread, (int, float))
                else f"  价差: {spread}\n"
            )
            if threshold > 0:
                status += f"  阈值: ±{threshold} (7天变化: {change:+.0f})\n"
            status += f"  更新: {updated}\n"
            return status
        return f"**{pair_name}:** 暂无数据\n"

    # 返回所有启用的标的状态
    all_data = get_all_status()
    if not all_data:
        return "暂无缓存数据\n"

    text = ""
    for name, data in all_data.items():
        zscore = data.get("zscore", "N/A")
        spread = data.get("spread", "N/A")
        threshold = data.get("threshold", 0)
        updated = data.get("updated_at", "未知")

        change_info = get_spread_change(name, days=7)
        change = change_info.get("change", 0) if change_info else 0

        text += f"**{name}:**\n"
        text += (
            f"  Z120: {zscore:.2f}"
            if isinstance(zscore, (int, float))
            else f"  Z120: {zscore}\n"
        )
        text += (
            f"  价差: {spread:.2f}"
            if isinstance(spread, (int, float))
            else f"  价差: {spread}\n"
        )
        if threshold > 0:
            text += f"  阈值: ±{threshold} (7天变化: {change:+.0f})\n"
        text += f"  更新: {updated}\n\n"

    return text


if __name__ == "__main__":
    print("测试多标缓存功能:")
    save_status("MNQ_MYM", 2.73, 1250.5, 1000.0, 250.0, 1000)
    save_status("HSTECH_MCH", 1.5, 500.0, 400.0, 100.0, 1000)
    print(format_status_text())
    print()
    print(format_status_text("MNQ_MYM"))
