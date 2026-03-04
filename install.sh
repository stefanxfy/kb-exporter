#!/bin/bash

# KB Exporter 安装脚本
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DEST="$HOME/.claude/skills/kb-exporter"

echo "Installing kb-exporter skill..."
echo "Source: $SCRIPT_DIR"
echo "Destination: $SKILL_DEST"
echo ""

# 创建目标目录
mkdir -p "$SKILL_DEST/scripts"

# 复制文件
echo "Copying SKILL.md..."
cp "$SCRIPT_DIR/SKILL.md" "$SKILL_DEST/"

echo "Copying scripts/export.py..."
cp "$SCRIPT_DIR/scripts/export.py" "$SKILL_DEST/scripts/"

echo ""
echo "✓ Installation complete!"
echo ""
echo "Installed files:"
ls -la "$SKILL_DEST"
ls -la "$SKILL_DEST/scripts/"
echo ""
echo "Please restart Claude Code to use the skill."
