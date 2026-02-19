"""环境配置管理模块

使用方法:
    from config.env_config import get_config, get_python_path, use_venv
    
    config = get_config()
    python = get_python_path()
    if use_venv():
        # 虚拟环境特定操作
        pass
"""

import os
import sys
from pathlib import Path
import yaml

# 缓存配置，避免重复读取
_config_cache = None

def load_settings():
    """加载 settings.yaml 配置"""
    global _config_cache
    
    if _config_cache is not None:
        return _config_cache
    
    # 找到配置文件（相对于当前文件）
    config_path = Path(__file__).parent / "settings.yaml"
    
    if not config_path.exists():
        raise FileNotFoundError(f"配置文件不存在: {config_path}")
    
    with open(config_path, 'r', encoding='utf-8') as f:
        _config_cache = yaml.safe_load(f)
    
    return _config_cache

def get_config():
    """
    获取当前环境的完整配置
    
    Returns:
        dict: 包含 python_path, project_root, use_venv 等配置
    """
    settings = load_settings()
    
    # 获取当前环境名称
    current_env = settings.get('current', 'local')
    
    # 获取环境配置
    env_config = settings.get('environments', {}).get(current_env, {})
    
    if not env_config:
        raise ValueError(f"未找到环境配置: {current_env}")
    
    return env_config

def get_python_path():
    """获取当前环境的 Python 解释器路径"""
    return get_config().get('python_path', sys.executable)

def get_project_root():
    """获取当前环境的项目根目录"""
    config_root = get_config().get('project_root')
    if config_root:
        return Path(config_root)
    # 默认使用当前文件的父目录
    return Path(__file__).parent.parent

def use_venv():
    """检查是否使用虚拟环境"""
    return get_config().get('use_venv', False)

def get_ib_port():
    """获取 IB Gateway 端口（通过 config 模块）"""
    from config import get_ibkr_port
    return get_ibkr_port()

def get_path(key):
    """
    获取相对路径（相对于 project_root）
    
    Args:
        key: 路径键名，如 'orders', 'account', 'data' 等
    
    Returns:
        Path: 绝对路径对象
    """
    settings = load_settings()
    project_root = get_project_root()
    
    # 从 settings.yaml 的 paths 部分获取
    relative_path = settings.get('paths', {}).get(key, key)
    
    return project_root / relative_path

def ensure_venv():
    """
    确保使用正确的 Python 解释器
    
    如果使用虚拟环境且当前不是虚拟环境的 Python，则重新执行脚本
    
    用法示例（放在脚本开头）:
        from config.env_config import ensure_venv
        ensure_venv()  # 如有需要，会重新执行脚本
    """
    if not use_venv():
        return  # 不使用虚拟环境，无需处理
    
    expected_python = get_python_path()
    current_python = sys.executable
    
    # 标准化路径进行比较
    expected = Path(expected_python).resolve()
    current = Path(current_python).resolve()
    
    if current != expected:
        print(f"[环境切换] 从 {current_python} 切换到 {expected_python}")
        # 使用正确的 Python 重新执行当前脚本
        os.execl(expected_python, expected_python, *sys.argv)

# 便捷函数：获取常用路径
def get_orders_path():
    """获取订单脚本路径"""
    return get_path('orders')

def get_account_path():
    """获取账户脚本路径"""
    return get_path('account')

def get_data_path():
    """获取数据目录路径"""
    return get_path('data')

def get_notify_path():
    """获取通知脚本路径"""
    return get_path('notify')

# 测试代码
if __name__ == "__main__":
    print("=" * 50)
    print("环境配置测试")
    print("=" * 50)
    
    config = get_config()
    print(f"\n当前环境: {load_settings().get('current')}")
    print(f"Python 路径: {get_python_path()}")
    print(f"项目根目录: {get_project_root()}")
    print(f"使用虚拟环境: {use_venv()}")
    
    print(f"\n常用路径:")
    print(f"  订单: {get_orders_path()}")
    print(f"  账户: {get_account_path()}")
    print(f"  数据: {get_data_path()}")
    print(f"  通知: {get_notify_path()}")
