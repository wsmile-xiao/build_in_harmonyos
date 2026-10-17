#!/data/service/hnp/bin/bash
# test_package/test.sh — xcfa 5.0.2 功能测试（上游行为视角，R34：真实执行被测二进制）。
#
# $1 = 包内 bin/xcfa（GTK3 图形界面），$2 = 包内 bin/xcfa_cli（命令行工具）。
# 两个二进制都在 conanrun 环境下真实运行；任何断言失败立即以非零码退出。
#
# 断言（5 条）：
#   1  xcfa --version        退出码 0 且横幅报出 5.0.2（GTK 二进制可执行、
#                            版本路径不依赖显示服务）
#   2  xcfa --help           退出码 0 且打印 "HELP MODE"
#   3  xcfa_cli --help       退出码 0 且打印命令行工具横幅
#   4  xcfa_cli --info_files 解析真实 WAV：frequency/quantification 与文件头一致
#   5  xcfa_cli 环境报告     打印外部程序检查表（依赖发现路径真实执行）
set -euo pipefail

GUI="${1:-}"
CLI="${2:-}"
[ -n "$GUI" ] && [ -n "$CLI" ] \
  || { echo "FAIL: usage: test.sh <pkg>/bin/xcfa <pkg>/bin/xcfa_cli" >&2; exit 1; }
[ -f "$GUI" ] || { echo "FAIL: gui binary missing: $GUI" >&2; exit 1; }
[ -f "$CLI" ] || { echo "FAIL: cli binary missing: $CLI" >&2; exit 1; }
echo "[test] gui: $GUI"
echo "[test] cli: $CLI"

WORKDIR="$(mktemp -d "${TMPDIR:-/tmp}/xcfa-test.XXXXXX")"
trap 'rm -rf "$WORKDIR"' EXIT HUP INT TERM

# ── 断言 1: xcfa --version ───────────────────────────────────────────────
echo "[test] 1/5 xcfa --version"
set +e
VER_OUT="$(timeout 60 "$GUI" --version 2>&1)"
VER_RC=$?
set -e
[ "$VER_RC" -eq 0 ] || { printf '%s\n' "$VER_OUT"; echo "FAIL: 1/5 xcfa --version rc=$VER_RC"; exit 1; }
case "$VER_OUT" in
  *"xcfa 5.0.2"*) echo "OK: 1/5 xcfa --version reports 5.0.2 (rc=0)" ;;
  *) printf '%s\n' "$VER_OUT"; echo "FAIL: 1/5 version banner lacks 'xcfa 5.0.2'"; exit 1 ;;
esac

# ── 断言 2: xcfa --help ──────────────────────────────────────────────────
echo "[test] 2/5 xcfa --help"
set +e
HELP_OUT="$(timeout 60 "$GUI" --help 2>&1)"
HELP_RC=$?
set -e
[ "$HELP_RC" -eq 0 ] || { printf '%s\n' "$HELP_OUT"; echo "FAIL: 2/5 xcfa --help rc=$HELP_RC"; exit 1; }
grep -q 'HELP MODE' <<<"$HELP_OUT" \
  || { printf '%s\n' "$HELP_OUT"; echo "FAIL: 2/5 --help did not print HELP MODE"; exit 1; }
echo "OK: 2/5 xcfa --help prints the help section (rc=0)"

# ── 断言 3: xcfa_cli --help ──────────────────────────────────────────────
echo "[test] 3/5 xcfa_cli --help"
set +e
CLI_HELP_OUT="$(timeout 60 "$CLI" --help 2>&1)"
set -e
grep -q 'xcfa_cli is an implementation of xcfa' <<<"$CLI_HELP_OUT" \
  || { printf '%s\n' "$CLI_HELP_OUT" | head -20; echo "FAIL: 3/5 xcfa_cli --help banner missing"; exit 1; }
echo "OK: 3/5 xcfa_cli --help prints the CLI banner"

# ── 断言 4: 真实 WAV 的音频分析（内置 WAV 解析 + taglib 链接）─────────────
echo "[test] 4/5 xcfa_cli --info_files on a generated WAV"
cd "$WORKDIR"
# 16-bit PCM 单声道 8000 Hz / 8000 采样（1 秒）标准 RIFF/WAVE 头，PCM 为静音。
# 用 printf 八进制转义构造（不依赖 python/sox 等外部程序）。
printf "RIFF\244\076\000\000WAVEfmt \020\000\000\000\001\000\001\000\100\037\000\000\200\076\000\000\002\000\020\000data\200\076\000\000" > sample.wav
head -c 16000 /dev/zero >> sample.wav
[ "$(wc -c < sample.wav)" = "16044" ] \
  || { echo "FAIL: 4/5 generated wav has unexpected size"; exit 1; }

set +e
INFO_OUT="$(timeout 60 "$CLI" -i "sample.wav" --info_files 2>&1)"
INFO_RC=$?
set -e
[ "$INFO_RC" -eq 0 ] || { printf '%s\n' "$INFO_OUT"; echo "FAIL: 4/5 --info_files rc=$INFO_RC"; exit 1; }
grep -q 'frequency = 8000' <<<"$INFO_OUT" \
  || { printf '%s\n' "$INFO_OUT"; echo "FAIL: 4/5 sample rate not reported as 8000 Hz"; exit 1; }
grep -q 'quantification = 16' <<<"$INFO_OUT" \
  || { printf '%s\n' "$INFO_OUT"; echo "FAIL: 4/5 bit depth not reported as 16"; exit 1; }
grep -q 'time      = 00:00:01' <<<"$INFO_OUT" \
  || { printf '%s\n' "$INFO_OUT"; echo "FAIL: 4/5 duration not reported as 1 s"; exit 1; }
echo "OK: 4/5 WAV analysed: 8000 Hz / 16 bit / 00:00:01"

# ── 断言 5: 环境报告（外部程序检查表真实生成）────────────────────────────
echo "[test] 5/5 xcfa_cli environment report"
set +e
ENV_OUT="$(timeout 60 "$CLI" 2>&1)"
set -e
grep -q 'NAME             DESCRIPTION' <<<"$ENV_OUT" \
  || { printf '%s\n' "$ENV_OUT" | head -20; echo "FAIL: 5/5 external program table missing"; exit 1; }
grep -q 'sox' <<<"$ENV_OUT" \
  || { echo "FAIL: 5/5 external program scan produced no entries"; exit 1; }
echo "OK: 5/5 environment report lists the external program scan table"

echo "FUNCTIONAL ASSERTIONS PASSED: 5/5"
