#!/usr/bin/env bash
set -e

echo "============================================================"
echo "Claude Usage Monitor - Uninstallation"
echo "============================================================"
echo ""

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

success() {
    echo -e "${GREEN}✅ $1${NC}"
}

warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

error() {
    echo -e "${RED}❌ $1${NC}"
}

# 확인 프롬프트
warning "This will remove all Claude Usage Monitor components"
read -p "Are you sure you want to uninstall? (y/N): " confirm
if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
    info "Uninstallation cancelled"
    exit 0
fi

echo ""

# 1. launchd 데몬 중지 및 제거
info "Stopping and removing launchd daemon..."

PLIST_FILE="$HOME/Library/LaunchAgents/com.claude.usage-monitor.plist"

if [[ -f "$PLIST_FILE" ]]; then
    launchctl stop com.claude.usage-monitor 2>/dev/null || true
    launchctl unload "$PLIST_FILE" 2>/dev/null || true
    rm "$PLIST_FILE"
    success "Daemon removed"
else
    info "Daemon not found (skipped)"
fi

echo ""

# 2. 실행 파일 제거
info "Removing executable scripts..."

if [[ -f "$HOME/.local/bin/claude-usage-monitor" ]]; then
    rm "$HOME/.local/bin/claude-usage-monitor"
    success "Removed claude-usage-monitor"
fi

if [[ -f "$HOME/.local/bin/claude-config" ]]; then
    rm "$HOME/.local/bin/claude-config"
    success "Removed claude-config"
fi

echo ""

# 3. SwiftBar 플러그인 제거
info "Removing SwiftBar plugin..."

SWIFTBAR_PLUGINS="$HOME/Library/Application Support/SwiftBar"

if [[ -f "$SWIFTBAR_PLUGINS/ClaudeUsage.1m.sh" ]]; then
    rm "$SWIFTBAR_PLUGINS/ClaudeUsage.1m.sh"
    success "Plugin removed"

    # SwiftBar 새로고침
    if pgrep -x "SwiftBar" > /dev/null; then
        info "Refreshing SwiftBar..."
        # SwiftBar 재시작
        osascript -e 'quit app "SwiftBar"' 2>/dev/null || true
        sleep 1
        open -a SwiftBar 2>/dev/null || true
    fi
else
    info "Plugin not found (skipped)"
fi

echo ""

# 4. 설정 파일 제거 (선택)
read -p "Remove configuration files? (~/.claude-monitor/) (y/N): " remove_config
if [[ "$remove_config" =~ ^[Yy]$ ]]; then
    if [[ -d "$HOME/.claude-monitor" ]]; then
        rm -rf "$HOME/.claude-monitor"
        success "Configuration removed"
    fi

    if [[ -f "$HOME/.claude_usage.json" ]]; then
        rm "$HOME/.claude_usage.json"
        success "Usage data removed"
    fi
else
    info "Configuration files kept at ~/.claude-monitor/"
fi

echo ""

# 5. 로그 파일 제거 (선택)
read -p "Remove log files? (~/Library/Logs/claude-usage-monitor.*) (y/N): " remove_logs
if [[ "$remove_logs" =~ ^[Yy]$ ]]; then
    rm -f "$HOME/Library/Logs/claude-usage-monitor.log"
    rm -f "$HOME/Library/Logs/claude-usage-monitor.err"
    success "Log files removed"
else
    info "Log files kept"
fi

echo ""

# 6. PATH 정리 안내
info "Note: If you added ~/.local/bin to PATH, you may want to remove it from:"
echo "      ~/.zshrc or ~/.bash_profile"

echo ""
echo "============================================================"
echo -e "${GREEN}✅ Uninstallation Complete!${NC}"
echo "============================================================"
echo ""
echo "Removed components:"
echo "  ✓ launchd daemon"
echo "  ✓ Executable scripts (~/.local/bin/)"
echo "  ✓ SwiftBar plugin"
if [[ "$remove_config" =~ ^[Yy]$ ]]; then
    echo "  ✓ Configuration files"
fi
if [[ "$remove_logs" =~ ^[Yy]$ ]]; then
    echo "  ✓ Log files"
fi

echo ""
echo "To reinstall, run: ./install.sh"
echo "============================================================"
