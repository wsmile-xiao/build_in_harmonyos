#!/data/service/hnp/bin/bash
set -eu

echo "[test] gprolog --version"
gprolog --version

cat > test.pl <<'EOF'
:- initialization(main).
main :- 2 + 3 =:= 5, write('PASS'), nl, halt.
EOF

echo "[test] gplc compile and link"
gplc -o test_program test.pl

echo "[test] run compiled consumer"
./test_program
