#!/usr/bin/env bash
# run_consumer.sh — 基于已安装包（conan cache package）编译链接并运行消费者用例。
# 仅使用包导出的公开头 fft.h 与库 libfft_c；模拟业务上层组件的真实消费方式。
set -u
SRC_DIR="$(cd "$(dirname "$0")" && pwd)"
ARCH_DIR="$(dirname "$SRC_DIR")"
PKG_REF="fft-c/3356ecd87d@ohpcd/stable"
CLANG="${CLANG:-/data/service/hnp/bin/clang}"
LOG="${LOG:-$SRC_DIR/consumer_run.log}"

# 解析已安装包路径（conan cache 权威路径：recipe 目录 ≠ package 目录，
# 必须带 package_id 才能拿到含 include/lib 的 package 文件夹）
PKG_ID="$(conan list "$PKG_REF:*" --format=json 2>/dev/null | python3 -c '
import json,sys
d = json.load(sys.stdin)
for rev in d.get("Local Cache", {}).get("fft-c/3356ecd87d@ohpcd/stable", {}).get("revisions", {}).values():
    for pid in rev.get("packages", {}):
        print(pid); break
    break
' | head -1)"
if [ -z "$PKG_ID" ]; then
    echo "[consumer] package not found: $PKG_REF (先运行 conan create)" >&2
    exit 2
fi
PKG_PATH="$(conan cache path "$PKG_REF:$PKG_ID" 2>/dev/null || true)"
if [ -z "$PKG_PATH" ] || [ ! -d "$PKG_PATH" ]; then
    echo "[consumer] package path not resolvable: $PKG_REF:$PKG_ID" >&2
    exit 2
fi
INC="$PKG_PATH/include"
LIBDIR="$PKG_PATH/lib"
echo "[consumer] package: $PKG_PATH"

"$CLANG" -O2 -I"$INC" -o "$SRC_DIR/consumer_fft_c" "$SRC_DIR/consumer_fft_c.c" \
    -L"$LIBDIR" -lfft_c -Wl,-rpath,"$LIBDIR" -lm
rc=$?
if [ $rc -ne 0 ]; then
    echo "[consumer] COMPILE FAILED rc=$rc" >&2
    exit $rc
fi
echo "[consumer] compile OK"

"$SRC_DIR/consumer_fft_c" 2>&1 | tee "$LOG"
rc=${PIPESTATUS[0]}
echo "[consumer] run exit=$rc log=$LOG"
exit $rc