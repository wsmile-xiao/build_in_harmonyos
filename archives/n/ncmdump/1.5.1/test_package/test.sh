#!/data/service/hnp/bin/bash
# test_package/test.sh — L1 consumer test for ncmdump 1.5.1.
#
# Invoked by conanfile.py's test() under the conanrun env, where PATH
# includes the installed bin/ — so `ncmdump` resolves by name.
#   1) `ncmdump -v` — binary runs, deps linked, version prints
#   2) decrypt the upstream official test.ncm fixture (passed as $1) and
#      verify the output audio exists, is non-empty and starts with a
#      known audio magic (ID3/MP3, fLaC/FLAC, OggS/OGG, RIFF/WAV).
#
# `set -e` 是安全的：唯一预期可能非零退出的命令（ncmdump 解密）已用
# `|| rc=$?` 显式接住，不会触发 set -e 误杀；其余命令失败应立即退出。
set -euo pipefail

ncm_path="${1:?usage: test.sh <test.ncm path>}"
echo "[step] ncmdump -v"
# 必须成功：验证二进制可执行、依赖库（taglib）链接正确、版本信息可打印
if ! ncmdump -v; then
    echo "FAIL: ncmdump -v exited non-zero" >&2
    exit 1
fi

echo "[step] decrypt test.ncm fixture"
# 官方样例 test.ncm（来自上游 test/ 目录，真实 NCM 加密文件）。
# ncmdump 输出文件名由音频格式决定（in.mp3 / in.flac 等），输出到 out/。
mkdir -p out
cp "$ncm_path" in.ncm
rc=0
output=$(ncmdump in.ncm -o out 2>&1) || rc=$?
printf '%s\n' "$output"
# 先判断信号崩溃（rc >= 128，被信号杀死），再判断普通非零退出，
# 避免 rc>=128 分支被 rc!=0 分支遮蔽成为死代码。
if [ "$rc" -ge 128 ]; then
    echo "FAIL: ncmdump crashed with signal $((rc - 128))" >&2
    exit 1
fi
if [ "$rc" -ne 0 ]; then
    echo "FAIL: ncmdump decryption exited non-zero (rc=$rc)" >&2
    exit 1
fi

echo "[step] verify decrypted audio output"
# 验证：输出目录存在、至少一个非空文件、且魔数是已知音频格式。
# 魔数比较使用完整 4 字节十六进制：ID3v2 头为 49 44 33 + 版本字节，
# 因此用 494433* 前缀匹配；fLaC/OggS/RIFF 为 4 字节精确魔数。
found=0
count=0
for f in out/*; do
    [ -f "$f" ] || continue
    count=$((count + 1))
    size=$(wc -c < "$f")
    magic=$(head -c 4 "$f" | od -An -tx1 | tr -d ' \n')
    echo "  output: $f size=$size magic=$magic"
    if [ "$size" -le 0 ]; then
        echo "FAIL: decrypted output is empty" >&2
        exit 1
    fi
    case "$magic" in
        494433*|664c6143|4f676753|52494646) found=1 ;;
    esac
done
if [ "$count" -lt 1 ]; then
    echo "FAIL: no decrypted audio file produced in out/" >&2
    exit 1
fi
if [ "$found" -ne 1 ]; then
    echo "FAIL: decrypted output is not a recognized audio format" >&2
    exit 1
fi

rm -rf out in.ncm
echo "PASS: ncmdump smoke test"
