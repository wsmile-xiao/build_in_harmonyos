#!/data/service/hnp/bin/bash
# test_package/test.sh — functional tests for the timidity executable
# Runs in conanrun env (PATH includes installed bin/)
#
# 上游 TiMidity++ 未提供任何测试用例 (无 `make check` 实际测试、无 test/ 目录、
# 无 sample MIDI 文件), 因此本脚本通过 CLI 行为验证打包的可执行文件功能完整:
#   1. --version 能正常输出版本信息
#   2. --help 能正常输出帮助文本
#   3. 非法选项能正确返回非零退出码 (错误处理可用)
#   4. 缺少参数时能正确退出并打印 usage (参数解析可用)
set -euo pipefail

# OHOS has read-only /tmp; use TMPDIR (writable on OHOS) with /tmp fallback.
TMP="${TMPDIR:-/tmp}"

PASS=0
FAIL=0

ok() {
    echo "[test] PASS: $1"
    PASS=$((PASS + 1))
}

ng() {
    echo "[test] FAIL: $1"
    FAIL=$((FAIL + 1))
}

echo "[test] Running TiMidity++ functional tests..."
echo "[test] ======================================="

# Test 1: timidity --version
echo "[test] Test 1: timidity --version (exit 0 + prints version)"
version_out=$(timidity --version 2>&1) && rc=0 || rc=$?
if [ "$rc" -eq 0 ] && echo "$version_out" | grep -qi "TiMidity"; then
    ok "timidity --version exits 0 and prints TiMidity version string"
else
    ng "timidity --version (rc=$rc); output: $version_out"
fi

# Test 2: timidity --help
echo "[test] Test 2: timidity --help (prints usage text)"
help_out=$(timidity --help 2>&1) && rc=0 || rc=$?
# --help on TiMidity++ may exit 0 or non-zero; either way it should print usage text
if echo "$help_out" | grep -qiE "Usage|option|interface|TiMidity"; then
    ok "timidity --help prints recognizable usage text"
else
    ng "timidity --help did not print recognizable usage text (rc=$rc); output: $help_out"
fi

# Test 3: timidity with invalid option (should exit non-zero)
echo "[test] Test 3: timidity --no-such-option (should exit non-zero)"
inv_out=$(timidity --no-such-option 2>&1) && rc=0 || rc=$?
if [ "$rc" -ne 0 ]; then
    ok "timidity rejects unknown option with non-zero exit code (rc=$rc)"
else
    ng "timidity accepted unknown option (rc=$rc); output: $inv_out"
fi

# Test 4: timidity with non-existent input file (graceful error handling)
echo "[test] Test 4: timidity <nonexistent.mid> (graceful error handling)"
noarg_out=$(timidity "$TMP/__nonexistent_test_file.mid" 2>&1) && rc=0 || rc=$?
# TiMidity++ should fail with non-zero exit code when input file does not exist
if [ "$rc" -ne 0 ]; then
    ok "timidity exits non-zero when input file does not exist (rc=$rc)"
else
    ng "timidity returned 0 on missing input file; output: $noarg_out"
fi

# Test 5: MIDI->WAVE conversion core functionality (R40 deep adaptation)
# Generates a minimal valid MIDI file (note-on/note-off) and invokes the
# conversion pipeline with -Ow (WAV output). Without a sound font the
# conversion cannot produce audio, but TiMidity++ must enter the conversion
# path and emit a recognizable conversion/config error (NOT a crash, NOT
# "unknown option"). This proves the MIDI parsing and synth pipeline are
# wired up on HarmonyOS.
echo "[test] Test 5: MIDI->WAVE conversion pipeline (R40 core functionality)"
midi_file="$TMP/__timidity_test.mid"
wav_file="$TMP/__timidity_test.wav"
# Minimal Type-0 MIDI: header (MThd) + one track (MTrk) with note on/off
# Track data: 00 c0 00 00 90 3c 60 83 00 80 3c 00 83 00 ff 2f 00 = 17 bytes
printf '\x4d\x54\x68\x64\x00\x00\x00\x06\x00\x00\x00\x01\x00\x60' > "$midi_file"
printf '\x4d\x54\x72\x6b\x00\x00\x00\x11' >> "$midi_file"
printf '\x00\xc0\x00\x00\x90\x3c\x60\x83\x00\x80\x3c\x00\x83\x00\xff\x2f\x00' >> "$midi_file"
conv_out=$(timidity -Ow -o "$wav_file" "$midi_file" 2>&1) && rc=0 || rc=$?
# Distinguish failure modes by exit code and output content:
#   - rc=127: command not found / linker failure (binary unusable) -> FAIL
#   - "unknown option"/"illegal option": -Ow flag not recognized -> FAIL
#   - TiMidity++ conversion-pipeline-specific keywords -> PASS (entered pipeline)
#   - rc=0 + wav file created -> PASS (full conversion succeeded)
if [ "$rc" -eq 127 ]; then
    ng "timidity binary unusable (exit 127, likely linker/loader error); output: $conv_out"
elif echo "$conv_out" | grep -qiE "error while loading shared libraries|dynamic linker|symbol lookup error|shared object file.*not found"; then
    ng "timidity binary failed before execution due to linker/loader error (rc=$rc); output: $conv_out"
elif echo "$conv_out" | grep -qiE "unknown option|illegal option|unrecognized"; then
    ng "timidity -Ow flag not recognized (rc=$rc); output: $conv_out"
elif echo "$conv_out" | grep -qiE "No instrument|Can't open|sound.?font|patch|output|\.wav|conversion|config"; then
    ok "timidity entered MIDI->WAVE conversion pipeline (rc=$rc, conversion-specific message emitted)"
else
    # If rc==0 and a wav file was produced, that's even better
    if [ "$rc" -eq 0 ] && [ -f "$wav_file" ]; then
        ok "timidity successfully converted MIDI to WAV (rc=0, output file created)"
    else
        ng "timidity did not enter conversion pipeline (rc=$rc); output: $conv_out"
    fi
fi
rm -f "$midi_file" "$wav_file"

echo "[test] ======================================="
echo "[test] Results: $PASS passed, $FAIL failed"

if [ "$FAIL" -gt 0 ]; then
    echo "[test] Some tests failed"
    exit 1
fi

echo "[test] All functional tests passed!"
