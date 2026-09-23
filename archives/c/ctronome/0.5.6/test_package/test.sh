#!/data/service/hnp/bin/bash
# test_package/test.sh — ctronome 功能测试（上游行为视角，R34：真实调用被测二进制）。
#
# $1（可选）= 包内 bin/ctronome；缺省时从 conanrun 环境的 PATH 查找。
# 断言 3 条：
#   1  -h 打印用法并以 0 退出（二进制可执行、参数解析正常）
#   2  -v 打印版本横幅
#   3  包内自带 WAV 采样可被解析并跑到音频输出阶段
set -euo pipefail

if [ -n "${1:-}" ]; then
  BIN="$1"
else
  BIN="$(command -v ctronome)"
fi
[ -x "$BIN" ] || { echo "FAIL: ctronome binary not executable: ${BIN:-<empty>}"; exit 1; }
echo "[step] binary: $BIN"
SHARE="$(cd "$(dirname "$BIN")/../share/ctronome" && pwd)"
echo "[step] share : $SHARE"

# 断言 1: -h 打印用法并以 0 退出（证明二进制可执行、参数解析正常）
help_out="$("$BIN" -h)"
case "$help_out" in
  *"usage: ctronome"*)
    echo "OK: 1/3 -h prints usage" ;;
  *)
    printf '%s\n' "$help_out"; echo "FAIL: 1/3 unexpected -h output"; exit 1 ;;
esac

# 断言 2: -v 打印版本横幅（该分支打印后继续执行；缺默认 WAV 时 rc 非 0，
# 故此处只看输出、不看退出码。上游版本号笔误见 notes.md）
set +e
ver_out="$("$BIN" -v 2>&1)"
set -e
case "$ver_out" in
  *"ctronome v"*)
    echo "OK: 2/3 -v prints version banner" ;;
  *)
    printf '%s\n' "$ver_out"; echo "FAIL: 2/3 unexpected -v output"; exit 1 ;;
esac

# 断言 3: 包内自带的 WAV 采样能被 ctronome 解析并进入音频输出阶段
wav1="$SHARE/metronome1.wav"
wav2="$SHARE/metronome2.wav"
if [ ! -f "$wav1" ] || [ ! -f "$wav2" ]; then
  echo "FAIL: 3/3 packaged wav samples missing"; ls -l "$SHARE"; exit 1
fi
set +e
out="$("$BIN" -b 120 -t 4 -c 1 -w1 "$wav1" -w2 "$wav2" 2>&1)"
rc=$?
set -e
printf '%s\n' "$out"
if printf '%s' "$out" | grep -qE "too short|only 8 and 16 bits"; then
  echo "FAIL: 3/3 packaged WAV samples were rejected by ctronome"; exit 1
fi
if printf '%s' "$out" | grep -qF "cannot open $wav1"; then
  echo "FAIL: 3/3 could not open wav1"; exit 1
fi
if printf '%s' "$out" | grep -qF "cannot open $wav2"; then
  echo "FAIL: 3/3 could not open wav2"; exit 1
fi
# HarmonyOS PC 无 OSS /dev/dsp：预期报 cannot open dsp device 且 rc=1；
# 若设备存在则真正播放成功、rc=0。两者都证明程序已跑到音频输出阶段。
if [ "$rc" -eq 0 ] || printf '%s' "$out" | grep -q "cannot open dsp device"; then
  echo "OK: 3/3 wav parsed, reached audio output stage (rc=$rc)"
else
  echo "FAIL: 3/3 unexpected ctronome behaviour (rc=$rc)"; exit 1
fi

echo "ALL 3 ASSERTIONS PASSED"
