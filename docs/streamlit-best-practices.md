# Streamlit 最佳实践

## 页面组织

- 每个页面是独立模块，暴露 `show()` 函数
- 使用 `st.session_state` 管理跨页面状态
- 页面间跳转使用 `st.rerun()`

```python
# 页面模块结构
def show():
    st.header("页面标题")
    # ... 页面内容
```

## 状态管理

```python
if "tickers" not in st.session_state:
    st.session_state.tickers = []

if "selected_symbol" not in st.session_state:
    st.session_state.selected_symbol = None
```

## 避免的问题

- 避免在 `show()` 顶层执行耗时操作 (阻塞UI)
- 耗时任务用 `st.spinner()` 包装
- 文件路径使用 `Path` 而非字符串拼接

## 状态持久化

现在使用 `config.py` 中的配置：
- `DATA_DIR` - 数据存储目录
- `WEBHOOK_URL` - 通知端点
- 运行时数据存储在 `data/` (已加入 `.gitignore`)
