#!/usr/bin/env bash
set -e

echo "============================================================"
echo "Claude Usage Monitor - Installation"
echo "============================================================"
echo ""

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 에러 처리
error_exit() {
    echo -e "${RED}❌ Error: $1${NC}" >&2
    exit 1
}

info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

success() {
    echo -e "${GREEN}✅ $1${NC}"
}

warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# 1. 사전 조건 확인
info "Checking prerequisites..."

# macOS 확인
if [[ "$OSTYPE" != "darwin"* ]]; then
    error_exit "This script is for macOS only"
fi

# Python 확인
if ! command -v python3 &> /dev/null; then
    error_exit "Python 3 is required but not installed"
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
info "Found Python $PYTHON_VERSION"

# Homebrew 확인
if ! command -v brew &> /dev/null; then
    warning "Homebrew not found"
    read -p "Install Homebrew? (y/N): " install_brew
    if [[ "$install_brew" =~ ^[Yy]$ ]]; then
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    else
        error_exit "Homebrew is required for SwiftBar installation"
    fi
fi

# jq 확인 (JSON 파싱용)
if ! command -v jq &> /dev/null; then
    info "Installing jq..."
    brew install jq || error_exit "Failed to install jq"
fi

success "Prerequisites check passed"
echo ""

# 2. SwiftBar 설치
info "Checking SwiftBar..."

if ! command -v swiftbar &> /dev/null; then
    read -p "SwiftBar not found. Install it? (Y/n): " install_swiftbar
    if [[ ! "$install_swiftbar" =~ ^[Nn]$ ]]; then
        info "Installing SwiftBar..."
        brew install --cask swiftbar || error_exit "Failed to install SwiftBar"
        success "SwiftBar installed"
    else
        warning "Skipping SwiftBar installation (manual install required later)"
    fi
else
    success "SwiftBar already installed"
fi

echo ""

# 3. 스크립트 설치
info "Installing monitor scripts..."

# 디렉토리 생성
mkdir -p "$HOME/.local/bin"
mkdir -p "$HOME/.claude-monitor"

# 스크립트 복사
cp src/monitor_daemon.py "$HOME/.local/bin/claude-usage-monitor"
cp src/config_manager.py "$HOME/.local/bin/claude-config"

# 실행 권한 부여
chmod +x "$HOME/.local/bin/claude-usage-monitor"
chmod +x "$HOME/.local/bin/claude-config"

success "Scripts installed to ~/.local/bin/"

# PATH 확인
if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
    warning "~/.local/bin is not in PATH"

    # zsh 확인
    if [[ "$SHELL" == */zsh ]]; then
        PROFILE="$HOME/.zshrc"
    else
        PROFILE="$HOME/.bash_profile"
    fi

    read -p "Add ~/.local/bin to PATH in $PROFILE? (Y/n): " add_path
    if [[ ! "$add_path" =~ ^[Nn]$ ]]; then
        echo '' >> "$PROFILE"
        echo '# Claude Monitor' >> "$PROFILE"
        echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$PROFILE"
        success "Added to $PROFILE (restart terminal to apply)"
    fi
fi

echo ""

# 4. SwiftBar 플러그인 설치
info "Installing SwiftBar plugin..."

# SwiftBar 플러그인 디렉토리 찾기
SWIFTBAR_PLUGINS="$HOME/Library/Application Support/SwiftBar"

# 디렉토리 생성 (없으면)
if [[ ! -d "$SWIFTBAR_PLUGINS" ]]; then
    mkdir -p "$SWIFTBAR_PLUGINS"
    success "Created plugins directory at $SWIFTBAR_PLUGINS"
fi

# 플러그인 복사
cp plugins/ClaudeUsage.1m.sh "$SWIFTBAR_PLUGINS/"
chmod +x "$SWIFTBAR_PLUGINS/ClaudeUsage.1m.sh"

success "Plugin installed to $SWIFTBAR_PLUGINS"

# SwiftBar 설정 자동 구성
info "Configuring SwiftBar..."

# SwiftBar가 실행 중인지 확인
if pgrep -x "SwiftBar" > /dev/null; then
    info "SwiftBar is already running"
else
    # SwiftBar 설정 파일에 플러그인 경로 설정
    defaults write com.ameba.SwiftBar PluginDirectory "$SWIFTBAR_PLUGINS"
    defaults write com.ameba.SwiftBar MakePluginExecutable -bool true
    success "SwiftBar preferences configured"

    # SwiftBar 실행
    info "Starting SwiftBar..."
    open -a SwiftBar
    sleep 2
fi

# SwiftBar에 플러그인 새로고침 요청
if pgrep -x "SwiftBar" > /dev/null; then
    osascript -e 'tell application "System Events" to tell process "SwiftBar" to click menu bar item 1 of menu bar 1' 2>/dev/null || true
    success "SwiftBar configured and running"
fi

echo ""

# 5. 초기 설정
info "Running initial configuration..."
echo ""

python3 "$HOME/.local/bin/claude-config"

echo ""

# 6. launchd 데몬 설정 (선택)
read -p "Install launchd daemon for automatic monitoring? (Y/n): " install_daemon
if [[ ! "$install_daemon" =~ ^[Nn]$ ]]; then
    info "Creating launchd service..."

    PLIST_FILE="$HOME/Library/LaunchAgents/com.claude.usage-monitor.plist"

    cat > "$PLIST_FILE" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.claude.usage-monitor</string>

    <key>ProgramArguments</key>
    <array>
        <string>$HOME/.local/bin/claude-usage-monitor</string>
        <string>--interval</string>
        <string>60</string>
    </array>

    <key>RunAtLoad</key>
    <true/>

    <key>KeepAlive</key>
    <true/>

    <key>StandardOutPath</key>
    <string>$HOME/Library/Logs/claude-usage-monitor.log</string>

    <key>StandardErrorPath</key>
    <string>$HOME/Library/Logs/claude-usage-monitor.err</string>

    <key>WorkingDirectory</key>
    <string>$HOME</string>
</dict>
</plist>
EOF

    # 로그 디렉토리 생성
    mkdir -p "$HOME/Library/Logs"

    # 데몬 로드
    launchctl load "$PLIST_FILE" 2>/dev/null || warning "launchd service load failed (may already be loaded)"
    launchctl start com.claude.usage-monitor 2>/dev/null || warning "launchd service start failed"

    success "Daemon installed and started"
else
    info "Skipping daemon installation (run manually: claude-usage-monitor)"
fi

echo ""
echo "============================================================"
echo -e "${GREEN}✅ Installation Complete!${NC}"
echo "============================================================"
echo ""
echo "Next steps:"
echo "  1. Open SwiftBar (or restart if already running)"
echo "  2. Click 'Refresh All' in SwiftBar menu"
echo "  3. Look for the usage indicator in your menu bar"
echo ""
echo "Commands:"
echo "  claude-usage-monitor          # Run daemon (if not using launchd)"
echo "  claude-config --change        # Change your plan"
echo "  cat ~/.claude_usage.json      # View current usage"
echo ""
echo "Files:"
echo "  Config:  ~/.claude-monitor/config.json"
echo "  Usage:   ~/.claude_usage.json"
echo "  Plugin:  $SWIFTBAR_PLUGINS/ClaudeUsage.1m.sh"
echo ""
echo "Logs:"
echo "  ~/Library/Logs/claude-usage-monitor.log"
echo "  ~/Library/Logs/claude-usage-monitor.err"
echo ""
echo "============================================================"
