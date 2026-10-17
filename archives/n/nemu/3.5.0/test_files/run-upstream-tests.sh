#!/bin/sh
# run-upstream-tests.sh — nemu 3.5.0 上游测试真跑入口（OHOS 设备）
#
# 用法（在 OHOS PC 设备上，具备 conan 缓存与 HNP 工具链的环境）：
#   bash archives/n/nemu/3.5.0/test_files/run-upstream-tests.sh \
#        <nemu-package-folder> <nemu-source-folder>
#
#   <nemu-package-folder>  conan create 的包产物目录（含 bin/nemu）
#   <nemu-source-folder>   上游源码树（含 test/）
#
# 前置条件（环境适配层的对外声明，详见 reports/test-report.md）：
#   1. tmux 3.4（archives/t/tmux/3.4 同仓配方，静态链接）
#   2. 可写 tmpfs 目录（/data/storage/el2/base/temp，OHOS 标准临时区；
#      根 /tmp 为只读 erofs——上游测试硬编码 /tmp 由本脚本的环境适配层重定向）
#   3. binary-sign-tool（OHOS ELF 代码签名；Conan 产物重签名后在设备执行）
#   4. qemu-system-x86_64/qemu-img 测试桩（本目录 *.stub；上游测试断言
#      的是 nemu 生成的 QEMU 命令行字符串，不实际启动 QEMU）
#
# 测试结果以 unittest 的标准输出为准（Ran N tests / OK / FAILED）。
set -eu

PKG_DIR="${1:?usage: run-upstream-tests.sh <pkg-dir> <src-dir>}"
SRC_DIR="${2:?usage: run-upstream-tests.sh <pkg-dir> <src-dir>}"
HERE="$(cd "$(dirname "$0")" && pwd)"   # test_files/

SANDBOX=/data/storage/el2/base/temp/nemu-ut$$
C2=${HOME}/.conan2/p

# ── 1. 沙箱布局（全部位于可写 tmpfs） ─────────────────────
mkdir -p "$SANDBOX/tmp/tmux-sock" "$SANDBOX/home" "$SANDBOX/nemu-bin" \
         "$SANDBOX/test-src" "$SANDBOX/qemu-stub"

# ── 2. nemu 二进制：复制 + 重签名（OHOS ELF 代码签名要求） ──
cp "$PKG_DIR/bin/nemu" "$SANDBOX/nemu-bin/nemu"
if command -v binary-sign-tool >/dev/null 2>&1; then
    binary-sign-tool sign -inFile "$SANDBOX/nemu-bin/nemu" \
        -outFile "$SANDBOX/nemu-bin/nemu.s" -selfSign 1 >/dev/null 2>&1 \
        && mv "$SANDBOX/nemu-bin/nemu.s" "$SANDBOX/nemu-bin/nemu"
fi
cp "$PKG_DIR/bin/ntty" "$SANDBOX/nemu-bin/ntty" 2>/dev/null || true
chmod +x "$SANDBOX/nemu-bin/"*

# ── 3. 测试源码与数据（tmpfs 副本；tmux 会话子进程无法读取
#      HMDFS 文件——实测 open() EACCES，见 reports/test-report.md） ──
cp -r "$SRC_DIR/test" "$SANDBOX/test-src/test"

# OVA 测试数据：上游 run.sh 用 gdown 从外网拉 dsl.ova（本环境不可达）。
# test_files/dsl.ovf + vmdk-descriptor 按上游 OVF 1.0 envelope 构造
# 功能等价的 dsl.ova（nemu 的 OVF import 断言只依赖 envelope 元数据与
# 文件名，磁盘内容不作要求——qemu-img convert 由桩执行）。
# 注意：必须是未压缩 tar（nemu 只 archive_read_support_format_tar，
# 未启用 gzip filter）。若源码树遗留 gzip 版 dsl.ova 则重新构造。
OVA_DST="$SANDBOX/test-src/test/testdata/dsl.ova"
if [ -f "$OVA_DST" ] && head -c 2 "$OVA_DST" | od -An -tx1 | grep -q "1f 8b"; then
    rm -f "$OVA_DST"   # gzip magic——重建
fi
if [ ! -f "$OVA_DST" ]; then
    mkdir -p "$(dirname "$OVA_DST")" "$SANDBOX/ova-stage"
    cp "$HERE/dsl.ovf" "$SANDBOX/ova-stage/"
    printf '# Disk DescriptorFile\nversion=1\nCID=fffffffe\nparentCID=ffffffff\ncreateType="monolithicSparse"\n\n# Extent description\nRW 2048 SPARSE "Damn_Small_Linux-disk1.vmdk"\n\n#DDB\nddb.virtualSize = "2048"\nddb.geometry.cylinders = "2"\nddb.geometry.heads = "64"\nddb.geometry.sectors = "32"\n' \
        > "$SANDBOX/ova-stage/Damn_Small_Linux-disk1.vmdk"
    dd if=/dev/zero bs=1024 count=512 2>/dev/null | tr '\0' 'D' \
        >> "$SANDBOX/ova-stage/Damn_Small_Linux-disk1.vmdk"
    (cd "$SANDBOX/ova-stage" && tar cf "$OVA_DST" \
        dsl.ovf Damn_Small_Linux-disk1.vmdk)
fi

# ── 4. 环境适配层 ────────────────────────────────────────
#   C 层（LD_PRELOAD）：/tmp 与 /usr/bin/qemu-* 重定向、getpwuid、
#     mkdtemp/chdir/statvfs/openat 等（nemu 二进制是普通懒绑定，
#     全部可拦截；python.org 构建的 libpython BIND_NOW 拦不到，
#     故 python 侧另有 sitecustomize 层）。
clang -shared -fPIC -O2 -o "$SANDBOX/libnemu_test_env.so" \
    "$HERE/nemu_test_env.c" -ldl

#   python 层（PYTHONPATH sitecustomize）：os.mkdir/stat/open、
#     builtins.open、pathlib、shutil、subprocess（相对命令名解析）。
mkdir -p "$SANDBOX/pysite"
cp "$HERE/sitecustomize.py" "$SANDBOX/pysite/"

#   qemu 桩：-M help 输出机型表（"pc ... (default)"），
#     qemu-img create/convert 语义。
cp "$HERE/qemu-system-x86_64.stub" "$SANDBOX/qemu-stub/qemu-system-x86_64"
cp "$HERE/qemu-img.stub" "$SANDBOX/qemu-stub/qemu-img"
chmod +x "$SANDBOX/qemu-stub/"*

# ── 5. 运行时库路径（conan 包缓存直连） ───────────────────
# 依赖 VirtualRunEnv 的库集合（libarchive→zstd 传递链等）。
RUN_LIBS=""
for pat in json-e8cb3b026c426 gettee8f94eaf5b0c5 libxma6fa3de616723 \
           libarb908e1abca34e zstda785316832b9b libus04e54d4f229a5; do
    d=$(ls -d ${C2}/${pat}/p/lib 2>/dev/null | head -1 || true)
    [ -n "$d" ] && RUN_LIBS="$RUN_LIBS:$d"
done
# ncurses terminfo（TUI 渲染需要 TERM=screen 的 terminfo 条目）
TERMINFO_DIR=$(ls -d ${C2}/ncurs780a5e6acf3cf/p/lib/terminfo 2>/dev/null | head -1 || true)
[ -z "$TERMINFO_DIR" ] && TERMINFO_DIR=$(find ${C2} -maxdepth 4 -type d -name terminfo 2>/dev/null | head -1 || true)

# ── 6. tmux 3.4（仓内 archives/t/tmux/3.4 配方，静态链接） ──
TMUX_BIN=$(command -v tmux || true)
[ -z "$TMUX_BIN" ] && TMUX_BIN=$(ls "$HOME/tmp/nemu-testrun/tmux-3.4/tmux" 2>/dev/null | head -1 || true)

# ── 7. 执行上游 unittest ──────────────────────────────────
cd "$SANDBOX/test-src/test"
PATH="$(dirname "$TMUX_BIN"):$PATH" \
NEMU_TMP_BASE="$SANDBOX/tmp" \
NEMU_FAKE_HOME="$SANDBOX/home" \
NEMU_QEMU_STUB_DIR="$SANDBOX/qemu-stub" \
TMUX_TMPDIR="$SANDBOX/tmp/tmux-sock" \
LD_PRELOAD="$SANDBOX/libnemu_test_env.so" \
LD_LIBRARY_PATH="${RUN_LIBS#:}" \
TERMINFO="$TERMINFO_DIR" \
TERM=screen \
NEMU_BIN_DIR="$SANDBOX/nemu-bin" \
QEMU_BIN_DIR=/usr/bin \
NEMU_TARGET_OS=OHOS \
NEMU_TEST_DIR="$SANDBOX/test-src/test" \
PYTHONPATH="$SANDBOX/pysite" \
python3 -m unittest -v vm_test ova_test

rc=$?
echo "== upstream tests exit: $rc =="
exit $rc
