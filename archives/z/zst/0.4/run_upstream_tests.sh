#!/data/service/hnp/bin/bash
# run_upstream_tests.sh — 在 HarmonyOS PC 上复现 zst 0.4 的上游测试套件（ctest）。
#
# 上游 tests/CMakeLists.txt 会把 tests/*.t 对每个可用压缩库各实例化一次
# （gzip/bzip2/xz/zstd），再加 tests/*.T 的工具无关用例，共 161 项。
#
# 依赖解析：直接用本机 conan 缓存的 zlib/bzip2/xz/zstd（与 recipe 相同的版本），
# 按 recipe 的做法把 4 个静态库暴露成私有 lib 目录再链接。
#
# 用法：
#   bash run_upstream_tests.sh [工作目录]     # 默认 $TMPDIR/zst-0.4-upstream
# 产出：
#   <工作目录>/build/zst          构建产物
#   <工作目录>/ctest.log          ctest 原始输出
#   <工作目录>/ctest-junit.xml    逐用例机器可读结果
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$HERE/../../../.." && pwd)"
PROFILE="$REPO_ROOT/ci/conan/profiles/ohos-aarch64"
WORK="${1:-${TMPDIR:-/tmp}/zst-0.4-upstream}"

rm -rf "$WORK"
mkdir -p "$WORK/static-libs"

# ── 源码：默认下载官方 tarball 并校验 SHA256（与 conandata.yml 一致）──
SRC_DIR="${ZST_SRC:-}"
if [ -z "$SRC_DIR" ]; then
    SRC_DIR="$WORK/src"
    TARBALL="$WORK/zst-0.4.tar.gz"
    mkdir -p "$SRC_DIR"
    curl -fsSL -o "$TARBALL" "https://github.com/kilobyte/zst/archive/refs/tags/v0.4.tar.gz"
    echo "9cb623ca402372981402d385e9fafdc168c0d60b481c6d61e4354de2728181e2  $TARBALL" | sha256sum -c - || {
        echo "源码 SHA256 校验失败"; exit 3; }
    tar -xzf "$TARBALL" -C "$SRC_DIR" --strip-components=1
fi
[ -f "$SRC_DIR/CMakeLists.txt" ] || { echo "找不到 zst 源码（设 ZST_SRC=）"; exit 2; }

# ── 依赖：本地 conan 缓存里的包目录 ──
resolve_dep() {   # $1=ref  →  echo 包目录
    conan install --requires="$1" -pr:h="$PROFILE" -pr:b="$PROFILE" --format=json 2>/dev/null \
        | python3 -c '
import json, sys
d = json.load(sys.stdin)
name = sys.argv[1].split("/")[0]
for node in d.get("graph", {}).get("nodes", {}).values():
    if str(node.get("ref", "")).startswith(name + "/"):
        print(node.get("package_folder") or "")
        break
' "$1"
}

ZSTD_DIR="$(resolve_dep zstd/1.5.7.1)"
ZLIB_DIR="$(resolve_dep zlib/1.3.1)"
BZIP2_DIR="$(resolve_dep bzip2/1.0.8.2)"
XZ_DIR="$(resolve_dep xz/5.6.2)"

# ── 测试期 PATH：必须能找到上游用例用到的工具 ──
# 1) OHOS toybox 的 cmp 不支持 -b，用 diffutils 的 GNU cmp
# 2) 用例直接调用原生 gzip/bzip2/xz/zstd（上游 .cirrus.yml 亦会 apt 安装这 4 个）
# 3) bzip2/xz/diff/grep 在 hnp 发行目录
DIFFUTILS_BIN="$(dirname "$(find /data/service/hnp -maxdepth 4 -path '*diff*/bin/cmp' 2>/dev/null | head -1)")"
export PATH="$DIFFUTILS_BIN:/data/service/hnp/bin:$ZSTD_DIR/bin:/usr/bin:/bin"

for p in "$ZLIB_DIR" "$BZIP2_DIR" "$XZ_DIR" "$ZSTD_DIR"; do
    for a in "$p"/lib/*.a; do ln -sf "$a" "$WORK/static-libs/$(basename "$a")"; done
done

SDK_TC="$(ls -d /data/service/hnp/ohos-sdk.org/*/ohos/native/build/cmake/ohos.toolchain.cmake | tail -1)"

INC="-I$ZLIB_DIR/include -I$BZIP2_DIR/include -I$XZ_DIR/include -I$ZSTD_DIR/include"
echo "[build] cmake configure + build"
cmake -G Ninja -B "$WORK/build" -S "$SRC_DIR" \
    -DCMAKE_TOOLCHAIN_FILE="$SDK_TC" \
    -DOHOS_ARCH=arm64-v8a \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
    -DCMAKE_C_FLAGS="$INC" \
    -DCMAKE_REQUIRED_LINK_OPTIONS="-L$WORK/static-libs" \
    -DCMAKE_EXE_LINKER_FLAGS="-L$WORK/static-libs" > "$WORK/cmake.log" 2>&1
cmake --build "$WORK/build" -- -j"$(nproc)" >> "$WORK/cmake.log" 2>&1

echo "[test] ctest -j8"
cd "$WORK/build"
ctest -j8 --output-junit "$WORK/ctest-junit.xml" 2>&1 | tee "$WORK/ctest.log"
echo "[test] 原始日志: $WORK/ctest.log"
echo "[test] junit:    $WORK/ctest-junit.xml"
