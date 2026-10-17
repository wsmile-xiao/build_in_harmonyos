#!/bin/sh
# test_ohos — colorized-logs 2.7 HarmonyOS PC 专项验证（自包含，可单独执行）
#
# 在真实鸿蒙 PC（aarch64, OHOS）上对最终 Conan 包做独立专项检查，
# 区别于上游内置自测（ctest testsuite）与 test_package 消费者用例：
#
#   T1  aarch64 ELF 验证（产物为 ELF64 AArch64，可在 OHOS 执行）
#   T2  OHOS 可执行位与宿主路径泄漏检查（无 /storage、/home 等宿主绝对路径）
#   T3  真实 ANSI 解码往返：ANSI 彩色日志 → ansi2txt 去色 → ansi2html 转义，
#       验证 OHOS 上 stdio/终端路径可运行且输出正确
#   T4  ttyrec 重放（二进制头含 NUL 的字节流经管道传输，验证 OHOS 管道 I/O）
#   T5  pipetty 伪终端分配（openpty 在 OHOS 内核路径可用）
#
# 用法：sh run_ohos_test.sh <已安装 bin 目录>
# 退出码：0=全部通过；非 0=有失败（打印首个错误）。
#
# 注意：输出捕获必须用临时文件而非 $(...) 命令替换——OHOS 上 shell 命令
# 替换会丢弃二进制流中的 NUL 字节（与上游 testsuite 相同的处理方式）。
set -u
BIN="${1:-}"
[ -n "$BIN" ] || { echo "usage: $0 <installed-bin-dir>"; exit 2; }
[ -d "$BIN" ] || { echo "FAIL: bin dir not found: $BIN"; exit 2; }
[ -x "$BIN/ansi2txt" ] || { echo "FAIL: ansi2txt not found in $BIN"; exit 2; }

TMP_ROOT="${TMPDIR:-/tmp}"
in_f="$TMP_ROOT/clohos-in.$$"
out_f="$TMP_ROOT/clohos-out.$$"
script_f="$TMP_ROOT/clohos-script.$$"
trap 'rm -f "$in_f" "$out_f" "$script_f"' EXIT

fail=0
chk() { # $1=name $2=result
    if [ "$2" = "0" ]; then echo "PASS: $1"; else echo "FAIL: $1"; fail=1; fi
}

echo "--- colorized-logs HarmonyOS 专项验证 (bin=$BIN) ---"

# T1: aarch64 ELF（ansi2txt 代表）
readelf -h "$BIN/ansi2txt" 2>/dev/null | grep -q "AArch64" && r=0 || r=1
chk "T1 aarch64 ELF (ELF64 AArch64)" "$r"

# T2: 宿主路径泄漏（构建机 /storage /home 绝对路径不得进入产物）
leak=$(strings "$BIN/ansi2txt" 2>/dev/null | grep -E '/storage/|/home/|/Users/' | head -1)
if [ -z "$leak" ]; then
    chk "T2 无宿主绝对路径泄漏" 0
else
    echo "  leak: $leak"
    chk "T2 无宿主绝对路径泄漏" 1
fi

# T3: ANSI 解码往返（真实日志场景：彩色警告 -> 文本 -> HTML）。
# 上游 testsuite 基准：'foo\e[1mbar\e[0m' 解码为 'foobar'（无中间空格）。
printf 'foo\033[1;31mbar\033[0m baz\n' > "$in_f"
"$BIN/ansi2txt" < "$in_f" > "$out_f" 2>&1
txt=$(cat "$out_f")
if [ "$txt" = "foobar baz" ]; then
    "$BIN/ansi2html" < "$in_f" > "$out_f" 2>&1
    case "$(cat "$out_f")" in *"<pre>"*) r=0;; *) r=1;; esac
    chk "T3 ANSI 解码往返 (txt='$txt', html转换)" "$r"
else
    echo "  txt='$txt'"
    chk "T3 ANSI 解码往返" 1
fi

# T4: ttyrec 重放（NUL 字节头经文件/管道 I/O）。
# ttyrec 头 len 字段（offset 8-11, LE）= 9；payload "hello tty\n" 恰好 9 字节。
printf 'aaaa10\a\0\t\0\0\0hello tty\n' > "$in_f"
"$BIN/ttyrec2ansi" < "$in_f" > "$out_f" 2>&1
tr_out=$(cat "$out_f")
if [ "$tr_out" = "hello tty" ]; then
    chk "T4 ttyrec 重放 (含 NUL 头)" 0
else
    echo "  out='$tr_out'"
    chk "T4 ttyrec 重放 (含 NUL 头)" 1
fi

# T5: pipetty 伪终端分配（脚本经文件作为 sh 参数，与上游 testsuite 同法）
printf 'test -t 0\nprintf "tty=%%d\\n" $?\n' > "$script_f"
"$BIN/pipetty" </dev/null sh "$script_f" > "$out_f" 2>&1
pt_out=$(cat "$out_f")
if [ "$pt_out" = "tty=1" ]; then
    chk "T5 pipetty 伪终端分配 (openpty)" 0
else
    echo "  out='$pt_out'"
    chk "T5 pipetty 伪终端分配 (openpty)" 1
fi

echo "--- colorized-logs OHOS 专项: $([ $fail = 0 ] && echo ALL PASS || echo FAILED) ---"
exit $fail