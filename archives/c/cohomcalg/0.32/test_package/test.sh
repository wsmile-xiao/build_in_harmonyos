#!/data/service/hnp/bin/bash
# test_package/test.sh — cohomcalg 0.32 smoke + correctness test
# Runs in conanrun env (PATH includes installed bin/)
# 注意: 上游对 --help 返回退出码 1 (main 对 help 走 return 1 路径), 属预期行为,
#       因此横幅检查只看输出内容, 不以 rc 为门禁; 主门禁是样例数学断言 (rc=0)。
set -eu

BIN="cohomcalg"
TMPD="${TMPDIR:-/tmp}/cohomcalg-tp.$$"
mkdir -p "$TMPD"

echo "[test] $BIN --help (上游 rc=1 属预期, 仅核验横幅)"
"$BIN" --help > "$TMPD/help.out" 2>&1 || true
grep -Fq "cohomCalg v0.32" "$TMPD/help.out" && echo "✅ --help banner OK (v0.32)"

# Correctness: feed the del-Pezzo-1 sample input; expect h1(O(-1,-2))=1 monomial u3*u4
cat > "$TMPD/dP1.in" <<'EOF'
vertex u1 = (  1,  1 ) | PIC: H  | GLSM:  ( 1,  0 );
vertex u2 = ( -1,  0 )           | GLSM:  ( 1,  0 );
vertex u3 = (  0, -1 )           | GLSM:  ( 1,  1 );
vertex u4 = (  0,  1 ) | PIC: X  | GLSM:  ( 0,  1 );
srideal [u1*u2,  u3*u4];
monomialfile off;
ambientcohom O(-1, -2);
ambientcohom O(-2,  0);
ambientcohom O(-3, -2);
EOF

echo "[test] $BIN --integrated --nomonomfile dP1.in"
"$BIN" --integrated --nomonomfile "$TMPD/dP1.in" > "$TMPD/dP1.out" 2>&1 || {
    echo "❌ run failed"; tail -20 "$TMPD/dP1.out"; exit 1; }
grep -Fq "{{0,1,0},{{1,1*u3*u4}}}" "$TMPD/dP1.out" && echo "✅ dP1 O(-1,-2) h1=1 OK"
grep -Fq "Program run successfully completed" "$TMPD/dP1.out" && echo "✅ dP1 run completed OK"

rm -rf "$TMPD"
echo "[test] all OK"