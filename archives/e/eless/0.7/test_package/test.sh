#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for eless script
# Runs in conanrun env (PATH includes installed bin/)
set -eu

echo "[test] eless -V"
# </dev/null: eless 在解析 -V 之前会检测 stdin；非交互环境下 (CI/buildbot,
# stdin 非 TTY) 脚本执行 `cat > $tmpfile` 等待 EOF 而永久阻塞。显式喂一个
# 立即 EOF 的空输入，让 cat 秒退，随后命中 -V 分支打印版本并 exit 0。
eless -V </dev/null 2>&1 | grep -q "Eless version" && echo "✅ eless -V OK" || {
    echo "❌ eless -V failed to print version"
    exit 1
}
