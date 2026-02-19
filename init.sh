#!/bin/bash
# =============================================================================
# Trading System - 初始化脚本
# 用于快速启动开发环境和验证系统状态
# =============================================================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 项目配置
PROJECT_NAME="Trading System"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"

# 打印带颜色的消息
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

# 分隔线
print_line() {
    echo "================================================================================"
}

# =============================================================================
# 会话恢复步骤（Anthropic 推荐）
# =============================================================================

print_line
echo -e "${BLUE}🚀 $PROJECT_NAME - 初始化脚本${NC}"
print_line

# 步骤 1: 确认当前目录
print_info "Step 1: 确认工作目录"
cd "$PROJECT_ROOT"
print_success "当前目录: $(pwd)"

# 步骤 2: 读取进度文件
print_info "Step 2: 读取会话进度"
if [ -f "docs/claude-progress.md" ]; then
    PROGRESS_DATE=$(head -20 docs/claude-progress.md | grep "最后更新" | cut -d: -f2- | xargs)
    print_success "进度文件: docs/claude-progress.md"
    print_info "最后更新: $PROGRESS_DATE"
else
    print_warning "未找到进度文件 docs/claude-progress.md"
fi

# 步骤 3: 读取功能清单
print_info "Step 3: 读取功能清单"
if [ -f "feature_list.json" ]; then
    if command -v jq &> /dev/null; then
        TOTAL=$(jq '.metrics.total_features' feature_list.json)
        COMPLETED=$(jq '.metrics.completed' feature_list.json)
        RATE=$(jq -r '.metrics.completion_rate' feature_list.json)
        print_success "功能清单: feature_list.json"
        print_info "进度: $COMPLETED/$TOTAL ($RATE)"
    else
        print_success "功能清单: feature_list.json (安装 jq 可查看详情)"
    fi
else
    print_error "未找到功能清单 feature_list.json"
    exit 1
fi

# 步骤 4: 检查 Git 状态
print_info "Step 4: 检查 Git 状态"
cd "$PROJECT_ROOT"
if [ -d ".git" ]; then
    GIT_BRANCH=$(git branch --show-current 2>/dev/null || echo "unknown")
    GIT_COMMIT=$(git log --oneline -1 2>/dev/null | cut -d' ' -f1 || echo "unknown")
    print_success "Git 分支: $GIT_BRANCH"
    print_info "最新提交: $GIT_COMMIT"
    
    # 检查未提交更改
    if [ -n "$(git status --porcelain 2>/dev/null)" ]; then
        print_warning "有未提交的更改"
        git status --short
    else
        print_success "工作区干净"
    fi
else
    print_warning "未找到 Git 仓库"
fi

# 步骤 5: 检测环境
print_info "Step 5: 检测运行环境"
if [ -d "/Users/openclaw/trading_env" ]; then
    ENV="remote"
    PYTHON_PATH="/Users/openclaw/trading_env/bin/python3"
    print_success "检测到环境: 远程 (OpenClaw)"
else
    ENV="local"
    PYTHON_PATH="python3"
    print_success "检测到环境: 本地开发"
fi

# 步骤 5.5: 自动修正环境配置
print_info "Step 5.5: 验证环境配置"
SETTINGS_FILE="$PROJECT_ROOT/config/settings.yaml"
if [ -f "$SETTINGS_FILE" ]; then
    CURRENT_ENV=$(grep "^current:" "$SETTINGS_FILE" | awk '{print $2}')
    if [ "$CURRENT_ENV" != "$ENV" ]; then
        print_warning "配置不匹配: current=$CURRENT_ENV, 实际环境=$ENV"
        print_info "自动修正配置..."
        sed -i.bak "s/^current: .*/current: $ENV/" "$SETTINGS_FILE"
        print_success "已将 current 设置为: $ENV"
    else
        print_success "环境配置正确: $ENV"
    fi
else
    print_warning "未找到 settings.yaml"
fi

# 步骤 6: 检查 Python 环境
print_info "Step 6: 检查 Python 环境"
if command -v "$PYTHON_PATH" &> /dev/null; then
    PYTHON_VERSION=$($PYTHON_PATH --version 2>&1)
    print_success "Python: $PYTHON_VERSION"
    
    # 检查关键依赖
    if $PYTHON_PATH -c "import ib_insync" 2>/dev/null; then
        print_success "依赖检查: ib_insync ✓"
    else
        print_warning "依赖检查: ib_insync ✗ (仅在远程需要)"
    fi
else
    print_error "未找到 Python: $PYTHON_PATH"
fi

# 步骤 7: 检查目录结构
print_info "Step 7: 检查目录结构"
REQUIRED_DIRS=("orders" "account" "notify" "config" "tests")
for dir in "${REQUIRED_DIRS[@]}"; do
    if [ -d "$PROJECT_ROOT/$dir" ]; then
        print_success "目录存在: $dir/"
    else
        print_error "目录缺失: $dir/"
    fi
done

# =============================================================================
# 服务启动（远程环境）
# =============================================================================

if [ "$ENV" = "remote" ]; then
    print_line
    print_info "Step 8: 启动 Webhook 服务"
    
    # 检查服务状态
    if launchctl list | grep -q "com.openclaw.webhook"; then
        print_info "服务已注册，检查运行状态..."
        
        # 测试健康检查
        if curl -s http://localhost:5002/health | grep -q '"status":"ok"'; then
            print_success "Webhook 服务运行正常"
            curl -s http://localhost:5002/health | jq . 2>/dev/null || curl -s http://localhost:5002/health
        else
            print_warning "服务未响应，尝试重启..."
            launchctl stop com.openclaw.webhook 2>/dev/null || true
            sleep 1
            launchctl start com.openclaw.webhook
            sleep 2
            
            if curl -s http://localhost:5002/health | grep -q '"status":"ok"'; then
                print_success "Webhook 服务已启动"
            else
                print_error "Webhook 服务启动失败"
                print_info "查看日志: tail -f ~/logs/webhook.error.log"
            fi
        fi
    else
        print_warning "服务未注册，加载 plist..."
        if [ -f "$HOME/Library/LaunchAgents/com.openclaw.webhook.plist" ]; then
            launchctl load "$HOME/Library/LaunchAgents/com.openclaw.webhook.plist"
            launchctl start com.openclaw.webhook
            print_success "服务已加载并启动"
        else
            print_error "未找到 plist 文件"
        fi
    fi
    
    # 显示访问地址
    print_line
    print_info "📡 服务访问地址:"
    echo "  - Health:  http://100.102.240.31:5002/health"
    echo "  - Webhook: http://100.102.240.31:5002/webhook"
fi

# =============================================================================
# 测试环境（可选）
# =============================================================================

print_line
print_info "🧪 运行基础测试..."

# 测试 1: 配置加载测试
if $PYTHON_PATH -c "import sys; sys.path.insert(0, '$PROJECT_ROOT'); from config.env_config import get_config; print('配置加载: OK')" 2>/dev/null; then
    print_success "配置系统: 正常"
else
    print_warning "配置系统: 需要检查"
fi

# 测试 2: 飞书配置检查
if [ -f "$PROJECT_ROOT/notify/config/feishu.yaml" ]; then
    print_success "飞书配置: 存在"
else
    print_warning "飞书配置: 不存在"
fi

# =============================================================================
# 总结
# =============================================================================

print_line
echo -e "${GREEN}✅ 初始化完成${NC}"
print_line

print_info "下一步建议:"
echo "  1. 查看功能清单:  cat feature_list.json | jq '.metrics'"
echo "  2. 查看进度:      cat docs/claude-progress.md"
echo "  3. 运行测试:      ./run_tests.sh"
echo "  4. 开始开发:      选择一个未完成的 feature"

if [ "$ENV" = "remote" ]; then
    print_line
    print_info "远程机器管理:"
    echo "  - 查看日志:  tail -f ~/logs/webhook.log"
    echo "  - 停止服务:  launchctl stop com.openclaw.webhook"
    echo "  - 重启服务:  launchctl start com.openclaw.webhook"
    echo "  - 更新代码:  git pull && launchctl restart com.openclaw.webhook"
fi

print_line
