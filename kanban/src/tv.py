"""TradingView CDP integration."""

import json
import subprocess
import time
import http.client

TV_HOST = "100.82.238.11"
TV_PORT = "9223"
TV_CLI = "/Users/wang/.opencode/workspace/tradingview-mcp/src/cli/index.js"
MULTI_WINDOW_SCRIPT = (
    "/Users/wang/.opencode/workspace/tradingview-mcp/get_window_data.cjs"
)


def run_tv_cmd(cmd_args, wait=0.5):
    cmd = f"TV_HOST={TV_HOST} TV_PORT={TV_PORT} node {TV_CLI} {' '.join(cmd_args)}"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15)
    if wait > 0:
        time.sleep(wait)
    if result.returncode == 0 and result.stdout:
        try:
            return json.loads(result.stdout)
        except:
            return None
    return None


def get_chart_targets():
    import socket

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(10)
    sock.connect((TV_HOST, int(TV_PORT)))
    request = f"GET /json/list HTTP/1.1\r\nHost: {TV_HOST}:{TV_PORT}\r\n\r\n".encode()
    sock.send(request)
    response = b""
    while True:
        try:
            chunk = sock.recv(4096)
            if not chunk:
                break
            response += chunk
            if len(response) > 20000:
                break
        except socket.timeout:
            break
    sock.close()
    text = response.decode("utf-8", errors="replace")
    parts = text.split("\r\n\r\n", 1)
    body = parts[1].strip() if len(parts) > 1 else text.strip()
    targets = json.loads(body)
    result = []
    for t in targets:
        if t.get("type") == "page" and "tradingview.com/chart" in t.get("url", ""):
            ws_url = t.get("webSocketDebuggerUrl", "")
            if ws_url:
                ws_url = ws_url.replace(
                    "ws://127.0.0.1:9222/", f"ws://{TV_HOST}:{TV_PORT}/"
                )
                ws_url = ws_url.replace("ws://127.0.0.1/", f"ws://{TV_HOST}:{TV_PORT}/")
                t["webSocketDebuggerUrl"] = ws_url
            result.append(t)
    return result


def get_all_tv_indicators(timeframe="5"):
    tf_map = {"1m": "1", "5m": "5", "15m": "15", "30m": "30", "1h": "60", "4h": "240"}
    tf_code = tf_map.get(timeframe, "5")

    try:
        targets = get_chart_targets()
        targets = list(reversed(targets))  # 反转以匹配 TV 窗口实际顺序
        if not targets:
            return get_single_tab_data(timeframe)

        results = []
        seen_symbols = set()

        for idx, target in enumerate(targets):
            ws_url = target.get("webSocketDebuggerUrl", "")
            if not ws_url:
                continue

            result = subprocess.run(
                ["node", MULTI_WINDOW_SCRIPT, ws_url, tf_code],
                capture_output=True,
                text=True,
                timeout=30,
                cwd="/Users/wang/.opencode/workspace/tradingview-mcp",
            )

            if result.returncode == 0 and result.stdout.strip():
                try:
                    data = json.loads(result.stdout.strip())
                    symbol = data.get("symbol", "N/A")

                    if symbol in seen_symbols:
                        continue
                    seen_symbols.add(symbol)

                    results.append(
                        {
                            "symbol": symbol,
                            "tab_index": idx,
                            "exchange": data.get("exchange", ""),
                            "description": data.get("description", ""),
                            "timeframe": data.get("timeframe", tf_code),
                            "quote": data.get("quote", {}),
                            "studies": data.get("studies", []),
                        }
                    )
                except json.JSONDecodeError:
                    pass

        if results:
            return {
                "tabs": results,
                "tab_count": len(results),
                "mode": "multi_window",
                "timeframe": timeframe,
            }

        return get_single_tab_data(timeframe)

    except Exception as e:
        import traceback

        print(f"get_all_tv_indicators error: {e}")
        traceback.print_exc()
        return get_single_tab_data(timeframe)


def get_single_tab_data(timeframe="5"):
    try:
        symbol_data = run_tv_cmd(["symbol"])
        quote_data = run_tv_cmd(["quote"])
        values_data = run_tv_cmd(["values"])
        if not symbol_data or not symbol_data.get("success"):
            return None
        all_data = [
            {
                "symbol": symbol_data.get("symbol", "N/A"),
                "description": symbol_data.get("description", ""),
                "exchange": quote_data.get("exchange", "") if quote_data else "",
                "timeframe": timeframe,
                "quote": {
                    "open": quote_data.get("open") if quote_data else None,
                    "high": quote_data.get("high") if quote_data else None,
                    "low": quote_data.get("low") if quote_data else None,
                    "close": quote_data.get("close") if quote_data else None,
                    "volume": quote_data.get("volume") if quote_data else None,
                }
                if quote_data
                else {},
                "studies": values_data.get("studies", []) if values_data else [],
            }
        ]
        return {"tabs": all_data, "tab_count": len(all_data), "timeframe": timeframe}
    except Exception as e:
        print(f"get_single_tab_data error: {e}")
        return None
