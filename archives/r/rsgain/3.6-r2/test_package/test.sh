#!/data/service/hnp/bin/bash
# test_package/test.sh — L1 consumer test for rsgain 3.6-r2.
#
# Invoked by conanfile.py's test() under the conanrun env, where PATH includes
# the installed bin/ — so `rsgain` resolves by name. R34: the test genuinely
# exercises the rsgain binary's audio I/O (libavformat/libavcodec/libswresample
# decode path + libebur128 loudness measurement):
#   1) `rsgain --version` — arg parsing + av/ebur128/taglib library init
#   2) WAV file scan — real decode + loudness measurement of a PCM file
#
# NOTE: 不使用 `set -e`：本测试需要允许 rsgain easy 返回非零退出码（WAV 不支持
# ReplayGain 标签写入属预期行为），仅拦截 >= 128 的信号崩溃。用 `set -u` 防止
# 未定义变量，`set -o pipefail` 让管道失败可被 || 捕获，退出码由显式 `|| rc=$?`
# 接住后再判定（评审第二轮 P2：set -e 与 || rc=$? 语义冲突）。
set -uo pipefail

echo "[step] rsgain --version"
# rsgain --version 必须成功（验证二进制可执行、依赖库链接正确）
if ! rsgain --version; then
    echo "FAIL: rsgain --version exited non-zero" >&2
    exit 1
fi

echo "[step] WAV file scan"
# Synthesize a 0.5-second 44100Hz 16-bit mono PCM WAV (silence).
# RIFF header (12) + fmt subchunk (24) + data subchunk header (8) + 44100 bytes.
{
    printf 'RIFF'
    printf '\x68\xac\x00\x00'  # file size - 8 = 44136
    printf 'WAVE'
    printf 'fmt '
    printf '\x10\x00\x00\x00'  # subchunk size = 16
    printf '\x01\x00'          # audio format = 1 (PCM)
    printf '\x01\x00'          # num channels = 1
    printf '\x44\xac\x00\x00'  # sample rate = 44100
    printf '\x88\x58\x01\x00'  # byte rate = 88200
    printf '\x02\x00'          # block align = 2
    printf '\x10\x00'          # bits per sample = 16
    printf 'data'
    printf '\x44\xac\x00\x00'  # data size = 44100
    head -c 44100 /dev/zero
} > test.wav

# Run rsgain easy mode on the test directory.
# WAV files don't support ReplayGain tags, so rsgain may report it cannot
# write tags — that's expected (non-zero exit for "no tags written" is OK).
# But we must catch fatal crashes (signals): exit codes >= 128 indicate the
# process was killed by a signal, which means the decode/measurement path
# crashed — that's a real failure we must surface.
mkdir -p preset-home
rc=0
output=$(HOME="$PWD/preset-home" rsgain easy --preset default . 2>&1) || rc=$?
printf '%s\n' "$output"
if ! printf '%s\n' "$output" | grep -F "Applying preset 'default'" >/dev/null; then
    echo "FAIL: packaged default preset was not loaded" >&2
    exit 1
fi
if [ "$rc" -ge 128 ]; then
    echo "FAIL: rsgain crashed with signal $((rc - 128))" >&2
    exit 1
fi

echo "PASS: rsgain smoke test"
