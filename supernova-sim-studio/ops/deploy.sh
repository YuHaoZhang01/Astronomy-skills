#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "用法：./snstudio deploy user@server" >&2
  exit 2
fi
SSH_TARGET="$1"
if [[ ! "$SSH_TARGET" =~ ^[A-Za-z0-9._-]+@[A-Za-z0-9._:-]+$ ]]; then
  echo "错误：SSH 目标必须是 user@host，且不能包含 shell 选项或空白字符。" >&2
  exit 2
fi
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SNEC_SOURCE="${SNEC_SOURCE_DIR:-/Users/zyh/Desktop/software/SNEC}"
TRANSFER_DIR="$(mktemp -d /tmp/snstudio-deploy.XXXXXX)"
trap 'rm -rf "$TRANSFER_DIR"' EXIT

echo "正在打包应用…"
tar -czf "$TRANSFER_DIR/app.tgz" \
  --exclude='.git' --exclude='.env' --exclude='.runtime' \
  --exclude='backend/.venv' --exclude='frontend/node_modules' --exclude='frontend/dist' \
  -C "$PROJECT_ROOT" .

if [[ -d "$SNEC_SOURCE/src" ]]; then
  echo "正在打包原版 SNEC 1.01 源码（排除既有输出与编译产物）…"
  tar -czf "$TRANSFER_DIR/snec-1.01.tgz" \
    --exclude='Data' --exclude='*.o' --exclude='*.mod' --exclude='./snec' \
    -C "$SNEC_SOURCE" .
else
  echo "警告：没有找到 $SNEC_SOURCE；服务器将只启用 SuperSNEC。" >&2
fi

cp "$PROJECT_ROOT/ops/bootstrap-server.sh" "$TRANSFER_DIR/bootstrap-server.sh"
REMOTE_STAGE="$(ssh "$SSH_TARGET" 'mktemp -d /tmp/snstudio-deploy.XXXXXX')"
if [[ ! "$REMOTE_STAGE" =~ ^/tmp/snstudio-deploy\.[A-Za-z0-9]+$ ]]; then
  echo "错误：服务器返回了不安全的暂存目录：$REMOTE_STAGE" >&2
  exit 1
fi
echo "正在传输到 $SSH_TARGET…"
scp "$TRANSFER_DIR/app.tgz" "$TRANSFER_DIR/bootstrap-server.sh" "$SSH_TARGET:$REMOTE_STAGE/"
if [[ -f "$TRANSFER_DIR/snec-1.01.tgz" ]]; then
  scp "$TRANSFER_DIR/snec-1.01.tgz" "$SSH_TARGET:$REMOTE_STAGE/"
fi

echo "开始远程引导；可能需要输入 sudo 密码与一次性 Tailscale auth key。"
ssh -t "$SSH_TARGET" "sudo bash '$REMOTE_STAGE/bootstrap-server.sh' '$REMOTE_STAGE'"
