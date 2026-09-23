#!/data/service/hnp/bin/bash
# test_package/test.sh — 消费者视角验证 peg-markdown CLI（R34：必须真实执行被测二进制）
#
# 断言一律用 `grep -qF`（固定字符串）：鸿蒙 worker 上存在两个 grep
# （/data/service/hnp/bin/grep = GNU grep 3.12，/usr/bin/grep → toybox 0.8.12），
# conanrun 环境里 PATH 会落到 toybox，而 toybox 的 BRE 不支持 "\|" 交替，
# 用 alternation 会造成断言假失败。
set -eu

BIN=markdown
fail() { echo "❌ $*" >&2; exit 1; }

command -v "$BIN" >/dev/null 2>&1 || fail "$BIN 不在 PATH 中"

echo "[test] $BIN --version"
ver=$(timeout 60 "$BIN" --version 2>&1 | head -1)
echo "       $ver"
echo "$ver" | grep -qF "peg-markdown version 0.4.14" || fail "--version 输出异常: $ver"

# 1) 文件入参路径
echo "[test] $BIN sample.md（文件入参 → HTML）"
printf '# Title\n\nSome *em* and **strong** text.\n' > sample.md
out=$(timeout 120 "$BIN" sample.md)
echo "$out" | grep -qF '<h1>Title</h1>' || fail "缺少 <h1>Title</h1>，实际: $out"
echo "$out" | grep -qF '<em>em</em>' || fail "缺少 <em>em</em>，实际: $out"
echo "$out" | grep -qF '<strong>strong</strong>' || fail "缺少 <strong>strong</strong>"

# 2) stdin 路径（回归护栏：char/int 的 EOF 判定若退化，这里会永久挂住 → timeout 判负）
echo "[test] echo | $BIN（stdin → HTML）"
out=$(printf 'para **bold**\n' | timeout 120 "$BIN")
echo "$out" | grep -qF '<p>para <strong>bold</strong></p>' || fail "stdin 转换结果异常: $out"

# 3) 其他输出格式
echo "[test] $BIN --to latex"
out=$(printf '# Title\n' | timeout 120 "$BIN" --to latex)
echo "$out" | grep -qF '\section{Title}' || fail "latex 输出异常: $out"

rm -f sample.md
echo "✅ peg-markdown CLI 全部断言通过（6 项）"
