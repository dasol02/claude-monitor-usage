#!/bin/bash

# Claude Usage Monitor - Installation Script
# macOS only (SwiftBar + fswatch required)

set -e

echo "🚀 Claude Usage Monitor Installation"
echo "======================================"
echo ""

# Check OS
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo "⚠️  This script is for macOS only (SwiftBar support)"
    echo "   For Windows/Linux: Use Chrome Extension only"
    exit 1
fi

# Check dependencies
echo "📦 Checking dependencies..."

# Check fswatch
if ! command -v fswatch &> /dev/null; then
    echo "❌ fswatch not found. Installing via Homebrew..."
    if ! command -v brew &> /dev/null; then
        echo "❌ Homebrew not installed. Please install it first:"
        echo "   /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
        exit 1
    fi
    brew install fswatch
fi

# Check jq
if ! command -v jq &> /dev/null; then
    echo "❌ jq not found. Installing via Homebrew..."
    brew install jq
fi

# Check SwiftBar
if [[ ! -d "$HOME/Library/Application Support/SwiftBar" ]]; then
    echo "⚠️  SwiftBar not found. Please install SwiftBar first:"
    echo "   https://github.com/swiftbar/SwiftBar/releases"
    echo ""
    read -p "Continue without SwiftBar? (Chrome Extension only) [y/N]: " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
    SKIP_SWIFTBAR=true
fi

echo "✅ Dependencies OK"
echo ""

# Install scripts to ~/.local/bin
echo "📥 Installing scripts to ~/.local/bin/..."
mkdir -p ~/.local/bin

cp scripts/claude-extension-watcher ~/.local/bin/
cp scripts/claude-start-extension-watcher ~/.local/bin/
cp scripts/claude-sync-from-extension ~/.local/bin/
cp scripts/claude-manual-update ~/.local/bin/

chmod +x ~/.local/bin/claude-extension-watcher
chmod +x ~/.local/bin/claude-start-extension-watcher
chmod +x ~/.local/bin/claude-sync-from-extension
chmod +x ~/.local/bin/claude-manual-update

echo "✅ Scripts installed"
echo ""

# Install SwiftBar plugin
if [[ "$SKIP_SWIFTBAR" != "true" ]]; then
    echo "📥 Installing SwiftBar plugin..."

    SWIFTBAR_PLUGIN_DIR="$HOME/Library/Application Support/SwiftBar"

    if [[ -f "$SWIFTBAR_PLUGIN_DIR/ClaudeUsage.1m.sh" ]]; then
        read -p "SwiftBar plugin already exists. Overwrite? [y/N]: " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            cp ClaudeUsage.1m.sh "$SWIFTBAR_PLUGIN_DIR/"
            chmod +x "$SWIFTBAR_PLUGIN_DIR/ClaudeUsage.1m.sh"
            echo "✅ SwiftBar plugin updated"
        else
            echo "⏭️  Skipped SwiftBar plugin"
        fi
    else
        cp ClaudeUsage.1m.sh "$SWIFTBAR_PLUGIN_DIR/"
        chmod +x "$SWIFTBAR_PLUGIN_DIR/ClaudeUsage.1m.sh"
        echo "✅ SwiftBar plugin installed"
    fi
    echo ""
fi

# Check if ~/.local/bin is in PATH
if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
    echo "⚠️  ~/.local/bin is not in PATH"
    echo ""
    echo "Add this line to your ~/.zshrc or ~/.bashrc:"
    echo "   export PATH=\"\$HOME/.local/bin:\$PATH\""
    echo ""
fi

echo "======================================"
echo "✅ Installation complete!"
echo ""
echo "📋 Next steps:"
echo ""
echo "1. Install Chrome Extension:"
echo "   - Open chrome://extensions/"
echo "   - Enable Developer mode"
echo "   - Click 'Load unpacked'"
echo "   - Select: $(pwd)/chrome-extension"
echo ""

if [[ "$SKIP_SWIFTBAR" != "true" ]]; then
    echo "2. Start Extension Watcher:"
    echo "   claude-start-extension-watcher"
    echo ""
    echo "3. Open SwiftBar and check the menu bar!"
    echo ""
fi

echo "📖 For detailed instructions, see README.md"
echo ""
