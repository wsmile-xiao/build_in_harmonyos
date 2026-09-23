#!/data/service/hnp/bin/bash
# test_package/test.sh — functional test for brandy (sbrandy) executable
# Runs in conanrun env (PATH includes installed bin/).
# Executes a real BBC BASIC program through the interpreter and asserts
# the output (R34: must actually exercise the packaged binary).
set -euo pipefail

echo "[test] sbrandy --version"
# </dev/null: 避免 sbrandy 打印版本后进入交互模式等待 stdin（CI 管道环境挂起）；
# 不用 head 截断管道（SIGPIPE 挂起），直接完整输出 + 退出码判定。
if ! sbrandy --version </dev/null 2>&1; then
    echo "❌ sbrandy --version failed"
    exit 1
fi

echo "[test] sbrandy executes BBC BASIC arithmetic + PRINT"
# BBC BASIC: PRINT evaluates expressions; also tests FOR/NEXT and IF.
cat > "$HOME/brandy_test.bas" <<'EOF'
FOR I% = 1 TO 3
  PRINT "v" + STR$(I%);
NEXT
PRINT
IF 2 + 3 = 5 THEN PRINT "arith-ok" ELSE PRINT "arith-fail"
EOF
OUT=$(sbrandy "$HOME/brandy_test.bas" </dev/null 2>&1)
echo "$OUT"
echo "$OUT" | grep -q "v1v2v3" || { echo "❌ FOR/NEXT/PRINT output missing"; exit 1; }
echo "$OUT" | grep -q "arith-ok" || { echo "❌ IF/arithmetic assertion failed"; exit 1; }
rm -f "$HOME/brandy_test.bas"
echo "✅ brandy functional test PASSED"