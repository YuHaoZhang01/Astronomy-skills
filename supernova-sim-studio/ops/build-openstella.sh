#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "用法：build-openstella.sh OPENSTELLA_ROOT" >&2
  exit 2
fi

OPENSTELLA_ROOT="$(cd "$1" && pwd)"
OPENSTELLA_COMMIT=6c6ad649a9987595da7fc57e735f640c5375e329
MODEL=m030307mhomo

if [[ ! -f "$OPENSTELLA_ROOT/obj/Stellaf90.mak" || ! -f "$OPENSTELLA_ROOT/obj/rparlnx.mak" ]]; then
  echo "错误：$OPENSTELLA_ROOT 不是完整的 OpenStella 源码树。" >&2
  exit 1
fi
if [[ "$(git -C "$OPENSTELLA_ROOT" rev-parse HEAD 2>/dev/null || true)" != "$OPENSTELLA_COMMIT" ]]; then
  echo "错误：OpenStella 必须固定在提交 $OPENSTELLA_COMMIT。" >&2
  exit 1
fi

if [[ "$(uname -s)" == "Darwin" ]]; then
  FORTRAN_BIN="${STELLA_FC:-$(command -v gfortran-15 || command -v gfortran || true)}"
  C_BIN="${STELLA_CC:-$(command -v gcc-15 || command -v gcc || true)}"
  MPI_BIN="${STELLA_MPIFC:-$(command -v mpif90 || true)}"
  SDK_ROOT="$(xcrun --sdk macosx --show-sdk-path)"
  FORTRAN_COMMAND="$FORTRAN_BIN -isysroot $SDK_ROOT"
  C_COMMAND="$C_BIN -isysroot $SDK_ROOT"
  MPI_COMMAND="env OMPI_FC=$FORTRAN_BIN $MPI_BIN -isysroot $SDK_ROOT"
else
  FORTRAN_BIN="${STELLA_FC:-$(command -v gfortran || true)}"
  C_BIN="${STELLA_CC:-$(command -v gcc || true)}"
  MPI_BIN="${STELLA_MPIFC:-$(command -v mpif90 || true)}"
  FORTRAN_COMMAND="$FORTRAN_BIN"
  C_COMMAND="$C_BIN"
  MPI_COMMAND="$MPI_BIN"
fi
if [[ -z "$FORTRAN_BIN" || -z "$C_BIN" || -z "$MPI_BIN" ]]; then
  echo "错误：构建 OpenStella 需要 gcc、gfortran 与 OpenMPI mpif90。" >&2
  exit 1
fi

echo "[1/5] 构建 Trefor 预处理器"
make -C "$OPENSTELLA_ROOT/trefor" "CC=$C_COMMAND -std=gnu89" clean
printf 'n\n' | make -C "$OPENSTELLA_ROOT/trefor" "CC=$C_COMMAND -std=gnu89" conf
make -C "$OPENSTELLA_ROOT/trefor" "CC=$C_COMMAND -std=gnu89" all
make -C "$OPENSTELLA_ROOT/trefor" "CC=$C_COMMAND -std=gnu89" all95
mkdir -p "$OPENSTELLA_ROOT/bin"
cp "$OPENSTELLA_ROOT/trefor/trf" "$OPENSTELLA_ROOT/trefor/trefor" \
  "$OPENSTELLA_ROOT/trefor/trefor95" "$OPENSTELLA_ROOT/bin/"
cp "$OPENSTELLA_ROOT/trefor/trfrc.sun" "$OPENSTELLA_ROOT/obj/.trfrc"

echo "[2/5] 准备官方 90-zone 模型的编译配置"
if [[ ! -f "$OPENSTELLA_ROOT/src/zone.inc" ]]; then
  cp "$OPENSTELLA_ROOT/src/zoneSample.inc" "$OPENSTELLA_ROOT/src/zone.inc"
fi
if [[ ! -f "$OPENSTELLA_ROOT/src/opacity.inc" ]]; then
  cp "$OPENSTELLA_ROOT/src/opacityHomo.inc" "$OPENSTELLA_ROOT/src/opacity.inc"
fi
for INCLUDE_FILE in "$OPENSTELLA_ROOT"/src/*.inc; do
  ln -sfn "$INCLUDE_FILE" "$OPENSTELLA_ROOT/obj/$(basename "$INCLUDE_FILE")"
done

echo "[3/5] 构建并生成官方初始模型"
PATH="$OPENSTELLA_ROOT/bin:$PATH" make -C "$OPENSTELLA_ROOT/obj" \
  -f Stellaf90.mak SYSTYPE=gfortran "FC=$FORTRAN_COMMAND" clean
PATH="$OPENSTELLA_ROOT/bin:$PATH" make -C "$OPENSTELLA_ROOT/obj" \
  -f Stellaf90.mak SYSTYPE=gfortran "FC=$FORTRAN_COMMAND" eve2
test -x "$OPENSTELLA_ROOT/run/eve/eve2.exe"
printf '%s\n' \
  'Data Result Model Opacity Rho ExtMod' \
  "'sn2.eve' 'res.tst' '$MODEL.mod' 'DummyOpafile' '$MODEL.rho' '../../modmake/$MODEL.hyd' '../../modmake/$MODEL.abn' '$MODEL.xni'" \
  > "$OPENSTELLA_ROOT/run/eve/eve.1"
(
  cd "$OPENSTELLA_ROOT/run/eve"
  ./eve2.exe > model-build.log 2>&1
)
for SUFFIX in mod rho xni; do
  test -s "$OPENSTELLA_ROOT/run/eve/$MODEL.$SUFFIX"
done

echo "[4/5] 用 MPI 生成官方 opacity tables"
PATH="$OPENSTELLA_ROOT/bin:$PATH" make -C "$OPENSTELLA_ROOT/obj" -f rparlnx.mak clean
PATH="$OPENSTELLA_ROOT/bin:$PATH" make -C "$OPENSTELLA_ROOT/obj" \
  -f rparlnx.mak "FC=$MPI_COMMAND" inner
test -x "$OPENSTELLA_ROOT/run/vladsf/xinsh.exe"
ln -sfn "$OPENSTELLA_ROOT/vladsf/lineatom.dat" \
  "$OPENSTELLA_ROOT/run/vladsf/lineatom.dat"
printf '%s\n' \
  'Model NiDist results opafile' \
  "'../eve/$MODEL.mod' '../eve/$MODEL.xni' 'ronfict1.res' '$MODEL.0'" \
  > "$OPENSTELLA_ROOT/run/vladsf/ronfict.1"
MPI_PROCESSES="${STELLA_MPI_PROCESSES:-6}"
MPI_ARGS=(-np "$MPI_PROCESSES" --oversubscribe)
if [[ "$(id -u)" -eq 0 ]]; then
  MPI_ARGS=(--allow-run-as-root "${MPI_ARGS[@]}")
fi
(
  cd "$OPENSTELLA_ROOT/run/vladsf"
  mpirun "${MPI_ARGS[@]}" ./xinsh.exe > opacity-build.log 2>&1
)
for INDEX in $(seq 1 "$MPI_PROCESSES"); do
  test -s "$OPENSTELLA_ROOT/run/vladsf/$MODEL.$INDEX"
done
test -s "$OPENSTELLA_ROOT/run/vladsf/$MODEL.ab"
if [[ "$(grep -c 'ronfict ends normally' "$OPENSTELLA_ROOT/run/vladsf/opacity-build.log")" -lt "$MPI_PROCESSES" ]]; then
  echo "错误：opacity builder 没有为所有 MPI rank 输出正常完成标志。" >&2
  exit 1
fi

echo "[5/5] 构建 STELLA 主程序并核验产物"
PATH="$OPENSTELLA_ROOT/bin:$PATH" make -C "$OPENSTELLA_ROOT/obj" \
  -f Stellaf90.mak SYSTYPE=gfortran "FC=$FORTRAN_COMMAND" stella6y12m
test -x "$OPENSTELLA_ROOT/run/strad/xstella6y12m.exe"
test -s "$OPENSTELLA_ROOT/run/strad/$MODEL.dat"
printf '%s\n' "$OPENSTELLA_COMMIT" > "$OPENSTELLA_ROOT/.snstudio-openstella-version"

echo "OpenStella 构建完成：$OPENSTELLA_ROOT"
