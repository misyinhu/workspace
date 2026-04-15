# IB Connection Pooling Refactoring Design

**Date**: 2026-04-15  
**Status**: ✅ Ready for Implementation  
**Goal**: Replace subprocess-based IB calls with direct function calls using persistent connections

## Problem Statement

### Current Architecture
- Webhook triggers commands via `subprocess.run()`
- Each command spawns a new Python process
- Each process connects to IB Gateway with its own clientId
- Multiple simultaneous requests cause clientId conflicts → blocking/timeout
- Each connection takes 3-5 seconds (connect → authenticate → query → disconnect)

### Issues
1. **Latency**: 3-5 seconds per query due to connection overhead
2. **Blocking**: Competing for clientId=0 causes timeout errors
3. **Resource waste**: Spawning processes for every request
4. **No connection reuse**: Every request = new TCP connection

## Proposed Architecture

### New Design
```
Webhook Request
      ↓
Direct Function Call (no subprocess)
      ↓
Shared IB Connection Pool (clientId=0)
      ↓
Result returned in milliseconds
```

### Key Changes
1. **Create IB Connection Manager** (`client/ib_connection.py`)
   - Singleton pattern for IB connection
   - Auto-reconnect on failure
   - Thread-safe access

2. **Refactor CLI scripts to functions**
   - `account/get_positions.py` → `account/positions.py` with `get_positions(ib)` function
   - Same pattern for all account/orders/data scripts

3. **Update webhook_bridge.py**
   - Remove subprocess calls
   - Import and call functions directly
   - Pass shared IB instance

## Files to Modify

### New Files
| File | Purpose |
|------|----------|
| `client/ib_connection.py` | Connection manager (singleton) |

### Modify Existing Files
| File | Change |
|------|---------|
| `notify/webhook_bridge.py` | Replace subprocess with direct function calls |
| `client/ibkr_client.py` | Keep for CLI scripts, add connection manager |
| `account/__init__.py` | Add function exports |
| `account/positions.py` | New: function version of get_positions.py |
| `account/trades.py` | New: function version of get_trades.py |
| `account/account_summary.py` | New: function version of get_account_summary.py |
| `orders/__init__.py` | Add function exports |
| `orders/place_order_func.py` | New: function version of place_order.py |
| `orders/cancel_order_func.py` | New: function version of cancel_order.py |
| `orders/query_orders.py` | New: function version of get_orders.py |
| `data/__init__.py` | Add function exports |
| `data/historical.py` | New: function version |
| `data/realtime.py` | New: function version |

## Implementation Phases

### Phase 1: Connection Manager (Highest Priority)
- Create `client/ib_connection.py` with singleton
- Add `get_ib_connection()` function
- Implement auto-reconnect logic

### Phase 2: Account Module Refactor
- Create `account/positions.py` with `get_positions(ib=None)`
- Update `COMMANDS` dict in webhook_bridge.py
- Test: `/持仓` command

### Phase 3: Orders Module Refactor
- Create order functions
- Test: `/订单` command and TradingView webhook

### Phase 4: Data Module Refactor (Optional)
- For future real-time data needs

## Connection Manager Design

```python
class IBConnection:
    _instance = None
    _ib = None
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def get_connection(self):
        """Get or create IB connection"""
        if not self._ib or not self._ib.isConnected():
            self._ib = IB()
            self._ib.connect(IBKR_HOST, IBKR_PORT, clientId=0)
        return self._ib
    
    def reconnect(self):
        """Force reconnect"""
        if self._ib and self._ib.isConnected():
            self._ib.disconnect()
        return self.get_connection()
```

## Backward Compatibility

- Keep CLI scripts (`get_positions.py`, etc.) for manual execution
- New function-based modules (`positions.py`, etc.) for webhook use
- Both use same logic, just different entry points

## Testing Plan

1. Deploy to CXClaw
2. Test `/持仓` command - should respond in <1s
3. Test multiple rapid commands - no blocking
4. Test TradingView webhook order placement
5. Monitor for connection issues

## Design Decisions (Confirmed by User)

### Reconnection Strategy
- **Auto-reconnect**: Connection manager detects disconnects and automatically reconnects
- User-facing commands should be transparent - no manual intervention needed

### ClientID Allocation
- **Webhook Service**: Always uses `clientId=0` (persistent connection)
- **CLI Scripts** (direct execution): Dynamically assign `clientId=2-9`
- This prevents conflicts between webhook and manual operations

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Connection drops mid-operation | Auto-reconnect in connection manager |
| Thread safety | Use threading.Lock for IB instance access |
| Gateway restart | Detect disconnect, auto-reconnect |
| Memory leaks | Limit connection pool size to 1 |

## Success Metrics

- [ ] `/持仓` responds in <1 second (vs 3-5s before)
- [ ] No blocking when 3+ commands issued simultaneously
- [ ] TradingView webhook orders execute reliably
- [ ] Connection auto-reconnects after IB Gateway restart