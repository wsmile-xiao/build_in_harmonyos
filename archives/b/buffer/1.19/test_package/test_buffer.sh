#!/bin/sh
# buffer 1.19 消费者用例 —— 被 git 跟踪的测试源（由 test_package/conanfile.py 的 test() 调用）
#
# 为什么必须有这个文件：
#   1) buffer 是管道过滤器、没有 --version/--help，冒烟测不到它的核心（POSIX 共享内存 +
#      进程间信号量 + 双进程环形缓冲）——每条用例都真实搬运数据并逐字节比对；
#   2) CI 的 L0c 要求 test_package/ 下存在被跟踪的测试源（.c/.cpp/.cc/.cxx/.sh/.py，
#      conanfile.py 除外）。只把断言内联在 conanfile.py 里，干净检出上 L0c 会判 fail，
#      而本地因为 conan 生成的 conanbuildenv-*.sh（被 .gitignore 忽略、永不进 PR）
#      会“看起来通过”——是假绿。
#
# 用法: sh test_buffer.sh [工作目录]   （默认 ./.buffer-selftest，跑完删除）
set -u

WORK="${1:-.buffer-selftest}"
rm -rf "$WORK"
mkdir -p "$WORK"

FAILED=0
cleanup() { rm -rf "$WORK"; }
trap cleanup EXIT INT TERM

check() {   # <名称> <期望> <实际>
    if [ "$2" = "$3" ]; then
        echo "PASS: $1"
    else
        echo "FAIL: $1 (expected=$2 actual=$3)"
        FAILED=1
    fi
}

# ── 用例 1：默认参数（10 KiB 块 × 99）下 256 KiB 往返逐字节一致 ──
head -c 262144 /dev/urandom > "$WORK/in_default.bin"
buffer < "$WORK/in_default.bin" > "$WORK/out_default.bin"
cmp -s "$WORK/in_default.bin" "$WORK/out_default.bin" && r=ok || r=diff
check "default-block 256KiB roundtrip" ok "$r"

# ── 用例 2：显式分块参数（-s 64 KiB -b 4 -m 512 KiB）下 1 MiB 往返 ──
head -c 1048576 /dev/urandom > "$WORK/in_tuned.bin"
buffer -s 65536 -b 4 -m 524288 < "$WORK/in_tuned.bin" > "$WORK/out_tuned.bin"
cmp -s "$WORK/in_tuned.bin" "$WORK/out_tuned.bin" && r=ok || r=diff
check "tuned -s/-b/-m 1MiB roundtrip" ok "$r"

# ── 用例 3：空输入 → 空输出（环形缓冲下界） ──
: > "$WORK/in_empty.bin"
buffer < "$WORK/in_empty.bin" > "$WORK/out_empty.bin"
check "empty input -> empty output" 0 "$(wc -c < "$WORK/out_empty.bin" | tr -d ' ')"

# ── 用例 4：-B 末块补齐（输出为 blocksize 整数倍，且前缀与输入逐字节一致） ──
head -c 200000 /dev/urandom > "$WORK/in_pad.bin"
buffer -B < "$WORK/in_pad.bin" > "$WORK/out_pad.bin"
out_sz=$(wc -c < "$WORK/out_pad.bin" | tr -d ' ')
head -c 200000 "$WORK/out_pad.bin" > "$WORK/out_pad_prefix.bin"
cmp -s "$WORK/in_pad.bin" "$WORK/out_pad_prefix.bin" && p=ok || p=diff
[ "$out_sz" -ge 200000 ] && g=ok || g=short
[ $((out_sz % 10240)) -eq 0 ] && m=ok || m=unaligned
check "-B pads last block to blocksize (in=200000 out=$out_sz)" "ok ok ok" "$p $g $m"

# ── 用例 5：-i/-o 文件模式与 stdin/stdout 语义等价 ──
buffer -i "$WORK/in_pad.bin" -o "$WORK/out_io.bin"
cmp -s "$WORK/in_pad.bin" "$WORK/out_io.bin" && r=ok || r=diff
check "-i/-o file mode equals stdin/stdout mode" ok "$r"

if [ "$FAILED" -ne 0 ]; then
    echo "buffer test_package: FAILED"
    exit 1
fi
echo "buffer test_package: 5/5 PASS"
exit 0
