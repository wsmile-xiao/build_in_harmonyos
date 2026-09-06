#!/data/service/hnp/bin/bash
# test_package/test.sh — R34 smoke tests for GNU poke 5.0 (consumer perspective)
# Runs in the conanrun env (PATH includes the installed bin/).
# Relocation env vars (POKEDATADIR/POKECONFIGDIR/POKEPICKLESDIR/POKEFMTAPPDIR)
# are exported by test_package/conanfile.py before this script runs.
set -u

PASS=0; FAIL=0
check() { # name expected actual
  if [ "$2" = "$3" ]; then
    echo "PASS: $1"
    PASS=$((PASS+1))
  else
    echo "FAIL: $1 (expected [$2], got [$3])"
    FAIL=$((FAIL+1))
  fi
}

WORK="$PWD/.smoke-work"
rm -rf "$WORK"; mkdir -p "$WORK"

# --- T1: poke --version -------------------------------------------------
V=$(poke --version 2>/dev/null | head -1)
case "$V" in
  *"GNU poke"*"5.0"*) echo "PASS: T1 poke --version ($V)"; PASS=$((PASS+1));;
  *)                  echo "FAIL: T1 poke --version (got: $V)"; FAIL=$((FAIL+1));;
esac

# --- T2: non-interactive pk evaluation (arith/shift/bitwise) ------------
# The shift operators are <<. and .>> (dotted, Poke language); the exact
# expected output doubles as an assertion (any compile error or unhandled
# exception would alter it).
cat > "$WORK/arith.pk" <<'EOF'
printf "A1=%v\n", 2 + 3;
printf "A2=%v\n", 1 <<. 4;
printf "A3=%v\n", 0xff .>> 4;
printf "A4=%v\n", 0x55 | 0xaa;
printf "A5=%v\n", (~0x0f) & 0xff;
printf "A6=%v\n", 7 % 2;
print "T2-DONE\n";
EOF
R=$(poke --color=no -s "$WORK/arith.pk" 2>/dev/null)
EXPECTED='A1=5
A2=16
A3=15
A4=255
A5=240
A6=1
T2-DONE'
check "T2 arithmetic/shift/bitwise evaluation" "$EXPECTED" "$R"

R=$(poke --color=no -c 'printf "C1=%v\n", 0x10 + 0x20;' 2>/dev/null)
check "T2b -c one-shot evaluation" "C1=48" "$R"

# --- T3: load a shipped pickle, verify the CRC-16/CCITT test vector -----
# 0x29b1 is the published check value for the ASCII string "123456789".
cat > "$WORK/pickle.pk" <<'EOF'
load "crc16.pk";
var data = [0x31UB, 0x32UB, 0x33UB, 0x34UB, 0x35UB, 0x36UB, 0x37UB, 0x38UB, 0x39UB];
var crc = crc16_ccitt (data);
printf "crc16_ccitt('123456789') = 0x%u16x\n", crc;
EOF
R=$(poke --color=no -s "$WORK/pickle.pk" 2>/dev/null)
check "T3 load crc16.pk pickle (standard vector)" \
      "crc16_ccitt('123456789') = 0x29b1" "$R"

# --- T4: pokefmt template processing (incl. pickle load) ----------------
# %{ ... }% holds statements, %( ... )% interpolates expressions; the
# template itself loads a pickle.  0x29B1 == 10673 decimal (uint<16> prints
# with the UH type suffix).
cat > "$WORK/fmt.pkfm" <<'EOF'
%{ var s = "poke"; load "crc16.pk"; var d = [0x31UB,0x32UB,0x33UB,0x34UB,0x35UB,0x36UB,0x37UB,0x38UB,0x39UB]; }%
tool: %(s)% arithmetic: %(2 + 3)% crc: %(crc16_ccitt (d))%
EOF
R=$(pokefmt 'var s = "poke";' < "$WORK/fmt.pkfm" 2>/dev/null)
echo "$R" | grep -q 'tool: "poke"' \
  && { echo "PASS: T4a pokefmt expression interpolation"; PASS=$((PASS+1)); } \
  || { echo "FAIL: T4a pokefmt expression interpolation (got: $R)"; FAIL=$((FAIL+1)); }
echo "$R" | grep -q 'arithmetic: 5' \
  && { echo "PASS: T4b pokefmt arithmetic"; PASS=$((PASS+1)); } \
  || { echo "FAIL: T4b pokefmt arithmetic (got: $R)"; FAIL=$((FAIL+1)); }
echo "$R" | grep -q 'crc: 10673UH' \
  && { echo "PASS: T4c pokefmt pickle load (0x29B1 == 10673)"; PASS=$((PASS+1)); } \
  || { echo "FAIL: T4c pokefmt pickle load (got: $R)"; FAIL=$((FAIL+1)); }

echo "===="
echo "TOTAL PASS=$PASS FAIL=$FAIL"
[ "$FAIL" -eq 0 ] || exit 1
