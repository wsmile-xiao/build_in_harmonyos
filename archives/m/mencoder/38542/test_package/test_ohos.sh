#!/usr/bin/env bash
set -euo pipefail

# 鸿蒙特有测试：OHOS 平台二进制一致性验证。
#
# 与 test.sh（消费者功能测试，覆盖上游 codecs 与真实编码链路）的区别：
# 本测试不验证编码功能，而验证产出的 mencoder 确实是面向 HarmonyOS
# 运行时构建的目标文件——即平台适配本身（ABI / OHOS 标识 / 运行时加载器 /
# 无 glibc 污染），这是桌面 Linux 构建不会产生、也无法通过的检查。
binary="${MENCODER_BIN:-$(command -v mencoder)}"

# readelf 输出一律先落盘再匹配：`readelf ... | grep -q` 在命中后 grep 立即退出
# 并关闭读端，CI 侧 LLVM 版 readelf 写剩余输出时遇 EPIPE，报
# "error: write on a pipe with no reader" 并以 74 退出（CI #48186 实测），
# 故本脚本不使用早退管道；临时目录取当前工作目录（CI 与本地均保证可写）。
tmpdir="./mencoder-ohos-conformance.$$"
mkdir -p "$tmpdir"
trap 'rm -rf "$tmpdir"' EXIT

fail() { echo "FAIL: $*" >&2; exit 1; }

[ -n "$binary" ] && [ -x "$binary" ] || fail "mencoder binary not found (MENCODER_BIN=${MENCODER_BIN:-unset})"
command -v readelf >/dev/null 2>&1 || fail "readelf not available in the test environment"

# 1. ABI：必须是 AArch64（OHOS arm64 目标）
readelf -h "$binary" >"$tmpdir/header.txt" 2>&1 || fail "readelf -h failed on $binary"
grep -q "AArch64" "$tmpdir/header.txt" || fail "not an AArch64 ELF: $binary"

# 2. OHOS 二进制标识：链接器写入的 .note.ohos.ident 段（glibc/Linux 构建无此段）
readelf -SW "$binary" >"$tmpdir/sections.txt" 2>&1 || fail "readelf -SW failed on $binary"
grep -q "\.note\.ohos\.ident" "$tmpdir/sections.txt" || fail ".note.ohos.ident section missing: $binary"

# 3. 运行时加载器：OHOS musl 加载器（而非 glibc 的 ld-linux-aarch64.so.1）
readelf -l "$binary" >"$tmpdir/segments.txt" 2>&1 || fail "readelf -l failed on $binary"
grep -q "ld-musl-aarch64\.so\.1" "$tmpdir/segments.txt" || fail "OHOS musl interpreter missing: $binary"

# 4. 无 glibc 污染：动态依赖中不得出现 glibc 运行时库
readelf -d "$binary" >"$tmpdir/dynamic.txt" 2>&1 || fail "readelf -d failed on $binary"
if grep -Eq "NEEDED.*(libc\.so\.6|ld-linux)" "$tmpdir/dynamic.txt"; then
    fail "glibc runtime dependency found in OHOS binary"
fi

# 5. 真实运行：内核经 .interp 以 OHOS musl 加载器启动进程且成功退出
#    （证明第 3 项声明的加载器在运行时确实可解析、依赖可加载，非仅静态字符串），
#    并断言真实编码后端 lavc（libavcodec）可用
"$binary" -ovc help >"$tmpdir/ovc.txt" 2>&1 || fail "mencoder -ovc help failed"
grep -q "lavc" "$tmpdir/ovc.txt" || fail "lavc video codec backend missing from -ovc help"

echo "OHOS platform conformance: PASS"
