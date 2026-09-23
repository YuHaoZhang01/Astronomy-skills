#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
INSTALL_ROOT="${1:-/Users/zyh/Desktop/software/OpenStella}"
OPENSTELLA_COMMIT=6c6ad649a9987595da7fc57e735f640c5375e329

if [[ -e "$INSTALL_ROOT" && ! -d "$INSTALL_ROOT/.git" ]]; then
  echo "错误：$INSTALL_ROOT 已存在但不是 OpenStella Git 仓库，不会覆盖。" >&2
  exit 1
fi
if [[ ! -d "$INSTALL_ROOT/.git" ]]; then
  git clone https://github.com/sblinnikov/OpenStella.git "$INSTALL_ROOT"
fi
git -C "$INSTALL_ROOT" fetch origin "$OPENSTELLA_COMMIT"
git -C "$INSTALL_ROOT" checkout --detach "$OPENSTELLA_COMMIT"
exec "$PROJECT_ROOT/ops/build-openstella.sh" "$INSTALL_ROOT"
