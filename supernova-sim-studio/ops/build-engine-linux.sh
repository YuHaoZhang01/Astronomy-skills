#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 2 ]]; then
  echo "用法：build-engine-linux.sh ENGINE_ROOT MAKE_INC" >&2
  exit 2
fi
ENGINE_ROOT="$1"
MAKE_INC="$2"
if [[ ! -f "$ENGINE_ROOT/src/Makefile" || ! -f "$MAKE_INC" ]]; then
  echo "错误：引擎源码或 Linux make.inc 不完整。" >&2
  exit 1
fi

docker run --rm \
  --mount "type=bind,src=$ENGINE_ROOT,dst=/engine" \
  --mount "type=bind,src=$MAKE_INC,dst=/config/make.inc,readonly" \
  debian:bookworm-slim \
  bash -euc '
    apt-get update >/dev/null
    apt-get install -y --no-install-recommends gfortran make liblapack-dev libblas-dev >/dev/null
    cp /config/make.inc /engine/make.inc
    cd /engine
    make clean >/dev/null 2>&1 || true
    make -j1
    test -x ./snec
  '
echo "已构建：$ENGINE_ROOT/snec"
