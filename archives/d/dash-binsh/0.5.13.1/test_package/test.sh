#!/bin/sh
# test_package consumer test for dash-binsh (Debian Almquist Shell).
# Runs the installed `dash` binary with real POSIX scripts and checks
# observable output + exit codes. Verifies a consumer can invoke the tool.
export PATH="$PATH:/system/bin"

echo "--- dash-binsh consumer verification ---"

# 1. arithmetic expansion: expect "8"
out1=$(dash -c 'echo $((3+5))')
[ "$out1" = "8" ] || { echo "FAIL: arithmetic expected 8 got [$out1]"; exit 1; }
echo "PASS 1: arithmetic expansion -> $out1"

# 2. function + parameter expansion: expect "ok"
out2=$(dash -c 'f(){ echo $1; }; f ok')
[ "$out2" = "ok" ] || { echo "FAIL: function expected ok got [$out2]"; exit 1; }
echo "PASS 2: function/param expansion -> $out2"

# 3. for loop: expect lines "1", "2", "3" (command substitution strips trailing newline)
out3=$(dash -c 'for i in 1 2 3; do echo $i; done')
flat3=$(printf '%s' "$out3" | tr '\n' ' ')
[ "$flat3" = "1 2 3" ] || { echo "FAIL: loop expected '1 2 3' got [$flat3]"; exit 1; }
echo "PASS 3: for loop -> $flat3"

# 4. command substitution + exit status propagation: expect "subst-ok"
out4=$(dash -c 'x=$(true) && echo subst-ok')
[ "$out4" = "subst-ok" ] || { echo "FAIL: substitution expected subst-ok got [$out4]"; exit 1; }
echo "PASS 4: command substitution -> $out4"

# 5. dash reports itself as a shell: expect dash
out5=$(dash -c 'echo $0')
case "$out5" in
  *dash*) echo "PASS 5: \$0 -> $out5" ;;
  *) echo "FAIL: \$0 expected dash got [$out5]"; exit 1 ;;
esac

echo "test dash-binsh 0.5.13.1: 5/5 functional checks PASS"
exit 0