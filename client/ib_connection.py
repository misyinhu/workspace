#!/usr/bin/env python3
"""
IB Connection Manager - Singleton pattern with auto-reconnect
用于 webhook 服务的持久化 IB 连接
"""

import os
import sys
import threading
import logging
from typing import Optional

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from ib_insync import IB
from config import load_config, get_ibkr_host, get_ibkr_port

# 加载配置
load_config()

logger = logging.getLogger(__name__)


class IBConnectionManager:
    """IB 连接管理器 - 单例模式，线程安全，支持自动重连"""
    
    _instance: Optional["IBConnectionManager"] = None
    _lock = threading.Lock()
    
    def __init__(self):
        self._ib: Optional[IB] = None
        self._host: str = get_ibkr_host()
        self._port: int = get_ibkr_port()
        self._client_id: int = 55  # Webhook 使用 clientId=55
        self._connected: bool = False
        self._connection_lock = threading.Lock()
    
    @classmethod
    def get_instance(cls) -> "IBConnectionManager":
        """获取单例实例"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance
    
    def get_connection(self) -> IB:
        """获取 IB 连接（自动重连）"""
        with self._connection_lock:
            if self._ib is None or not self._ib.isConnected():
                self._connect()
            return self._ib
    
    def _connect(self):
        """建立连接"""
        try:
            if self._ib is not None and self._ib.isConnected():
                return
            
            logger.info(f"🔌 连接 IB Gateway: {self._host}:{self._port} (clientId={self._client_id})")
            self._ib = IB()
            self._ib.connect(self._host, self._port, clientId=self._client_id, timeout=10)
            self._connected = True
            logger.info("✅ IB 连接已建立")
        except Exception as e:
            logger.error(f"❌ IB 连接失败: {e}")
            self._connected = False
            raise
    
    def reconnect(self) -> IB:
        """强制重连"""
        with self._connection_lock:
            logger.info("🔄 强制重连 IB...")
            if self._ib is not None and self._ib.isConnected():
                try:
                    self._ib.disconnect()
                except:
                    pass
            self._ib = None
            self._connected = False
            return self._connect_and_return()
    
    def _connect_and_return(self) -> IB:
        """连接并返回 IB 实例"""
        self._connect()
        return self._ib
    
    def is_connected(self) -> bool:
        """检查连接状态"""
        if self._ib is None:
            return False
        return self._ib.isConnected()
    
    def disconnect(self):
        """断开连接"""
        with self._connection_lock:
            if self._ib is not None and self._ib.isConnected():
                try:
                    self._ib.disconnect()
                    logger.info("🔌 IB 连接已断开")
                except:
                    pass
            self._connected = False
    
    def get_ib(self) -> Optional[IB]:
        """获取原始 IB 实例（不自动重连）"""
        return self._ib


# 全局访问函数
_ib_connection_manager: Optional[IBConnectionManager] = None


def get_ib_connection() -> IB:
    """获取 IB 连接的全局函数"""
    global _ib_connection_manager
    if _ib_connection_manager is None:
        _ib_connection_manager = IBConnectionManager.get_instance()
    return _ib_connection_manager.get_connection()


def get_ib_manager() -> IBConnectionManager:
    """获取连接管理器实例"""
    global _ib_connection_manager
    if _ib_connection_manager is None:
        _ib_connection_manager = IBConnectionManager.get_instance()
    return _ib_connection_manager


# 兼容旧代码 - 提供类似原有 get_client_id 的功能
def get_client_id() -> int:
    """获取 clientId (webhook 固定为 0)"""
    return 0


if __name__ == "__main__":
    # 测试连接
    print("测试 IB Connection Manager...")
    ib = get_ib_connection()
    print(f"连接状态: {ib.isConnected()}")
    print(f"账户: {ib.accountSummary()[:2]}")
    get_ib_manager().disconnect()
    print("完成")