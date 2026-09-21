#!/usr/bin/env bash
# test_package/test_tools.sh — libetonyek-tools 消费者测试（鸿蒙 PC / aarch64）
#
# 用法: bash test_tools.sh <已安装包的 bin 目录>
#
# 这是消费者（装了包之后拿到 CLI 的用户）视角的断言，不依赖构建树。
# 任何一条失败即整体退出码非 0 —— 因此把包里的 bin/ 移走后本脚本必须失败
# （CI L1e / R34 的破坏性反向验证）。

set -u

BIN="${1:-bin}"
TOOLS="key2raw numbers2raw pages2raw key2text numbers2text pages2text numbers2csv pages2html key2xhtml"

PASS=0
FAIL=0
ok()   { PASS=$((PASS+1)); printf '  [PASS] %s\n' "$1"; }
bad()  { FAIL=$((FAIL+1)); printf '  [FAIL] %s\n' "$1"; }
check() { # check <描述> <条件结果 0/非0>
  if [ "$2" -eq 0 ]; then ok "$1"; else bad "$1"; fi
}

WORK="$(mktemp -d "${TMPDIR:-.}/eonyek-test.XXXXXX")"
trap 'rm -rf "$WORK"' EXIT

printf '== 1. 安装与可执行性 ==\n'
[ -d "$BIN" ] || { bad "bin 目录不存在: $BIN"; printf 'TOTAL=1 PASS=0 FAIL=1\n'; exit 1; }
for t in $TOOLS; do
  if [ -f "$BIN/$t" ] && [ -x "$BIN/$t" ]; then ok "$t 已安装且可执行"; else bad "$t 缺失或不可执行"; fi
done

printf '== 2. 产物是 HarmonyOS aarch64 ELF ==\n'
for t in $TOOLS; do
  [ -f "$BIN/$t" ] || { bad "$t 无法读取 ELF 头"; continue; }
  magic="$(od -An -tx1 -N4 "$BIN/$t" | tr -d ' \n')"
  # e_machine 在 ELF64 头偏移 18，AArch64 = 0xB7，小端两字节
  mach="$(od -An -tx1 -j18 -N2 "$BIN/$t" | tr -d ' \n')"
  if [ "$magic" = "7f454c46" ] && [ "$mach" = "b700" ]; then
    ok "$t 是 ELF64 / EM_AARCH64"
  else
    bad "$t ELF 头异常 magic=$magic e_machine=$mach"
  fi
done

printf '== 3. 版本自述与包版本一致 ==\n'
for t in $TOOLS; do
  out="$("$BIN/$t" --version 2>&1 </dev/null)"; rc=$?
  case "$out" in
    *"0.1.12"*) ok "$t --version 报 0.1.12 (rc=$rc)";;
    *) bad "$t --version 未报 0.1.12：$(printf '%s' "$out" | head -1)";;
  esac
done

printf '== 4. 无参数与 --help 的用法路径 ==\n'
for t in $TOOLS; do
  out="$("$BIN/$t" --help 2>&1 </dev/null)"; rc=$?
  case "$out" in
    *Usage*|*usage*) ok "$t --help 打印用法 (rc=$rc)";;
    *) bad "$t --help 无用法输出";;
  esac
done

printf '== 5. 输入文件不存在时必须失败并给出诊断 ==\n'
for t in $TOOLS; do
  out="$("$BIN/$t" "$WORK/no-such-file.key" 2>&1 </dev/null)"; rc=$?
  if [ "$rc" -ne 0 ] && [ -n "$out" ]; then
    ok "$t 缺文件时非零退出且有诊断"
  else
    bad "$t 缺文件时未正确失败 (rc=$rc)"
  fi
done

printf '== 6. 非 iWork 输入必须被格式识别拒绝 ==\n'
printf 'not an iwork document at all\n' > "$WORK/garbage.txt"
for t in $TOOLS; do
  out="$("$BIN/$t" "$WORK/garbage.txt" 2>&1 </dev/null)"; rc=$?
  if [ "$rc" -ne 0 ] && [ -n "$out" ]; then
    ok "$t 拒绝无法识别的文档"
  else
    bad "$t 对垃圾输入未报错 (rc=$rc)"
  fi
done

# 格式探测器（EtonyekDocument::detect）按文档类型把输入路由给对应的解析器，
# 因此"像 Numbers 的 XML"必须由 numbers2* 送进 Numbers 解析器（诊断是
# 解析/生成失败），而由 pages2*/key2* 直接报"不支持的格式"。两条诊断文本不同
# → 断言非恒真：产品若退化成统一 echo，这一组里必有一半失败。
# numbers2csv 的诊断文本与另两个不同（它失败在 CSV 生成阶段），按工具各自
# 实测文本精确断言。语料在脚本内合成（不往包里塞上游二进制文档）。
printf '== 7. 探测器按类型分流（两组诊断必须不同） ==\n'
cat > "$WORK/numbersish.xml" <<'XMLEOF'
<?xml version="1.0"?>
<ls:document xmlns:sfa="http://developer.apple.com/namespaces/sfa" xmlns:ls="http://developer.apple.com/namespaces/ls" ls:version="92008102400" sfa:ID="LSDocumentModel-0">
</ls:document>
XMLEOF
for spec in "numbers2raw:Parsing failed" "numbers2text:Parsing failed" \
            "numbers2csv:CSV Generation failed"; do
  t="${spec%%:*}"; want="${spec##*:}"
  out="$("$BIN/$t" "$WORK/numbersish.xml" 2>&1 </dev/null)"; rc=$?
  case "$out" in
    *"$want"*) ok "$t 把 Numbers XML 送进 Numbers 处理并报「$want」(rc=$rc)";;
    *) bad "$t 的诊断不是「$want」：$(printf '%s' "$out" | head -1)";;
  esac
done
for t in pages2raw pages2text pages2html key2raw key2text key2xhtml; do
  out="$("$BIN/$t" "$WORK/numbersish.xml" 2>&1 </dev/null)"; rc=$?
  case "$out" in
    *"Unsupported file format"*) ok "$t 拒收 Numbers XML 并报 Unsupported file format (rc=$rc)";;
    *) bad "$t 对 Numbers XML 的诊断不是 Unsupported file format：$(printf '%s' "$out" | head -1)";;
  esac
done

printf '== 8. --version 与 --help 的退出码语义 != 转换失败 ==\n'
# --version 是成功路径（rc=0），--help/无参数走 printUsage() 并返回 -1 → 255；
# 真解析失败返回 1。三种退出码互不相同，可反证二进制没有被 wrapper 吞掉。
v_rc=0; "$BIN/key2raw" --version >/dev/null 2>&1 || v_rc=$?
h_rc=0; "$BIN/key2raw" --help >/dev/null 2>&1 || h_rc=$?
f_rc=0; "$BIN/key2raw" "$WORK/no-such-file.key" >/dev/null 2>&1 || f_rc=$?
[ "$v_rc" -eq 0 ] && ok "--version 退出码 0" || bad "--version 退出码 $v_rc（应为 0）"
[ "$h_rc" -ne 0 ] && [ "$h_rc" -ne 1 ] && ok "--help 退出码 $h_rc（printUsage 的 -1，非解析失败的 1）" || bad "--help 退出码 $h_rc 与解析失败码混淆"
[ "$f_rc" -eq 1 ] && ok "缺文件的转换失败退出码恰为 1" || bad "转换失败退出码 $f_rc（应为 1）"
[ "$v_rc" != "$f_rc" ] && ok "--version 与转换失败的退出码可区分" || bad "--version 与转换失败退出码相同，无法区分"

printf 'TOTAL=%d PASS=%d FAIL=%d\n' "$((PASS+FAIL))" "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ] || exit 1
