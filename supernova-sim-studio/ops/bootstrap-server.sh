#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 || ! "$1" =~ ^/tmp/snstudio-deploy\.[A-Za-z0-9]+$ ]]; then
  echo "错误：必须提供由部署器创建的安全暂存目录。" >&2
  exit 2
fi
STAGE_ROOT="$1"
APP_ARCHIVE="$STAGE_ROOT/app.tgz"
SNEC_ARCHIVE="$STAGE_ROOT/snec-1.01.tgz"
INSTALL_ROOT=/opt/snstudio
APP_ROOT="$INSTALL_ROOT/app"
ENGINE_ROOT="$INSTALL_ROOT/engines"
SUPERSNEC_COMMIT=318fc4160a28a6299db9f58966b79c8d2d35a440
OPENSTELLA_COMMIT=6c6ad649a9987595da7fc57e735f640c5375e329

if [[ "$(id -u)" -ne 0 ]]; then
  echo "错误：bootstrap-server.sh 必须通过 sudo 运行。" >&2
  exit 1
fi
chmod -R go-rwx "$STAGE_ROOT"
trap 'rm -rf -- "$STAGE_ROOT"' EXIT
if [[ ! -f /etc/os-release ]]; then
  echo "错误：仅支持 Ubuntu 24.04。" >&2
  exit 1
fi
. /etc/os-release
if [[ "${ID:-}" != "ubuntu" || "${VERSION_ID:-}" != "24.04" ]]; then
  echo "错误：首版仅支持 Ubuntu 24.04，当前为 ${PRETTY_NAME:-unknown}。" >&2
  exit 1
fi
if [[ ! -f "$APP_ARCHIVE" ]]; then
  echo "错误：缺少 $APP_ARCHIVE。" >&2
  exit 1
fi

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y \
  ca-certificates curl gnupg git tar \
  gcc gfortran make openmpi-bin libopenmpi-dev

if ! command -v docker >/dev/null 2>&1; then
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
  chmod a+r /etc/apt/keyrings/docker.asc
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu noble stable" > /etc/apt/sources.list.d/docker.list
  apt-get update
  apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
fi
systemctl enable --now docker

if ! command -v tailscale >/dev/null 2>&1; then
  curl -fsSL https://pkgs.tailscale.com/stable/ubuntu/noble.noarmor.gpg -o /usr/share/keyrings/tailscale-archive-keyring.gpg
  curl -fsSL https://pkgs.tailscale.com/stable/ubuntu/noble.tailscale-keyring.list -o /etc/apt/sources.list.d/tailscale.list
  apt-get update
  apt-get install -y tailscale
fi
systemctl enable --now tailscaled
if ! tailscale status >/dev/null 2>&1; then
  read -r -s -p "请输入一次性 Tailscale auth key: " TAILSCALE_JOIN_KEY
  echo
  if [[ -z "$TAILSCALE_JOIN_KEY" ]]; then
    echo "错误：Tailscale auth key 不能为空。" >&2
    exit 1
  fi
  tailscale up --auth-key="$TAILSCALE_JOIN_KEY"
  unset TAILSCALE_JOIN_KEY
fi

mkdir -p "$APP_ROOT" "$ENGINE_ROOT" /var/lib/snstudio
find "$APP_ROOT" -mindepth 1 -maxdepth 1 -exec rm -rf -- {} +
tar -xzf "$APP_ARCHIVE" -C "$APP_ROOT"

if [[ ! -d "$ENGINE_ROOT/supersnec/.git" ]]; then
  rm -rf "$ENGINE_ROOT/supersnec"
  git clone https://github.com/cfremling/SuperSNEC.git "$ENGINE_ROOT/supersnec"
fi
git -C "$ENGINE_ROOT/supersnec" fetch --all --tags
git -C "$ENGINE_ROOT/supersnec" checkout --detach "$SUPERSNEC_COMMIT"

if [[ ! -d "$ENGINE_ROOT/openstella/.git" ]]; then
  rm -rf "$ENGINE_ROOT/openstella"
  git clone https://github.com/sblinnikov/OpenStella.git "$ENGINE_ROOT/openstella"
fi
git -C "$ENGINE_ROOT/openstella" fetch origin "$OPENSTELLA_COMMIT"
git -C "$ENGINE_ROOT/openstella" checkout --detach "$OPENSTELLA_COMMIT"

if [[ -f "$SNEC_ARCHIVE" ]]; then
  rm -rf "$ENGINE_ROOT/snec-1.01"
  mkdir -p "$ENGINE_ROOT/snec-1.01"
  tar -xzf "$SNEC_ARCHIVE" -C "$ENGINE_ROOT/snec-1.01"
else
  mkdir -p "$ENGINE_ROOT/snec-1.01"
fi

"$APP_ROOT/ops/build-engine-linux.sh" "$ENGINE_ROOT/supersnec" "$APP_ROOT/ops/make.inc.linux"
if [[ -f "$ENGINE_ROOT/snec-1.01/src/Makefile" ]]; then
  "$APP_ROOT/ops/build-engine-linux.sh" "$ENGINE_ROOT/snec-1.01" "$APP_ROOT/ops/make.inc.linux"
fi
"$APP_ROOT/ops/build-openstella.sh" "$ENGINE_ROOT/openstella"

cd "$APP_ROOT"
export SNSTUDIO_VERSION="$(date -u +%Y%m%d%H%M%S)"
docker compose -p snstudio build
docker compose -p snstudio up -d --remove-orphans

for attempt in $(seq 1 60); do
  if curl -fsS http://127.0.0.1:8787/api/health >/dev/null; then
    break
  fi
  if [[ "$attempt" -eq 60 ]]; then
    docker compose -p snstudio logs --tail=200
    echo "错误：服务健康检查超时。" >&2
    exit 1
  fi
  sleep 2
done

docker compose -p snstudio exec -T api python - <<'PY'
import json
import urllib.request

with urllib.request.urlopen("http://127.0.0.1:8787/api/v1/engines", timeout=10) as response:
    engines = {item["id"]: item for item in json.load(response)}
stella = engines.get("stella")
if not stella or not stella.get("enabled"):
    raise SystemExit(f"STELLA 部署自检失败：{stella}")
print(f"STELLA 自检通过：{stella['version']}")
PY

tailscale serve reset >/dev/null 2>&1 || true
tailscale serve --bg http://127.0.0.1:8787
echo
echo "部署完成。仅可通过 Tailnet 访问："
tailscale serve status
