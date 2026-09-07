#!/data/service/hnp/bin/bash
# test_package/test.sh — R34 smoke tests for posh 0.14.6 (consumer perspective)
# Runs in the conanrun env (PATH includes the installed bin/).
# All temp files live under $PWD/.smoke-work: OHOS /tmp is read-only (E002).
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

# --- T1: $POSH_VERSION assertion ---------------------------------------
# posh has NO -version/-V/--version option upstream; the version is
# exposed through the $POSH_VERSION shell variable (this is exactly how
# upstream's own tests/version.t checks it).  Upstream quirk: the
# maintainer forgot to bump acinclude.m4 POSH_VERSION for the 0.14.6
# release, so the binary reports 0.14.5 (upstream version.t expects
# 0.14.5 too).  The assertion accepts either value and reports which one
# it saw; neither is an adaptation defect.
V=$(posh -c 'echo $POSH_VERSION' 2>/dev/null)
case "$V" in
  0.14.5|0.14.6)
    echo "PASS: T1 \$POSH_VERSION reports $V (0.14.5 = upstream forgot-to-bump, see notes.md)"
    PASS=$((PASS+1));;
  *)
    echo "FAIL: T1 \$POSH_VERSION (expected 0.14.5 or 0.14.6, got: $V)"
    FAIL=$((FAIL+1));;
esac

# --- T2: arithmetic expansion -------------------------------------------
check "T2 arithmetic \$((3*7+1))" "22" "$(posh -c 'echo $((3*7+1))')"
check "T2b arithmetic \$((16/5))"  "3"  "$(posh -c 'echo $((16/5))')"

# --- T3: variable expansion ----------------------------------------------
check "T3 variable expansion" "helloworld" \
  "$(posh -c 'x=hello; echo ${x}world')"
check "T3b default expansion" "fallback" \
  "$(posh -c 'unset x; echo ${x:-fallback}')"

# --- T4: pipeline ---------------------------------------------------------
check "T4 pipeline (sort|uniq)" "1
2
3" "$(printf '3\n1\n2\n1\n3\n' | posh -c 'sort | uniq')"

# --- T5: redirection (file under $PWD: /tmp is read-only on OHOS, E002) ---
# "redir-ok\n" = 9 bytes (8 chars + newline)
R=$(posh -c "printf 'redir-ok\n' > '$WORK/out.txt'; wc -c < '$WORK/out.txt'" 2>&1 | tr -d ' ')
check "T5 redirection + wc byte count" "9" "$R"

# --- T6: exit-code propagation --------------------------------------------
posh -c 'exit 42' 2>/dev/null
check "T6 exit code propagation (exit 42)" "42" "$?"
posh -c 'false' 2>/dev/null
check "T6b builtin false -> 1" "1" "$?"
posh -c 'true' 2>/dev/null
check "T6c builtin true -> 0" "0" "$?"

# --- T7: functions ---------------------------------------------------------
check "T7 function definition + call" "21" \
  "$(posh -c 'f() { echo $(($1 * $2)); }; f 3 7')"

# --- T8: if/else -----------------------------------------------------------
check "T8 if/else branch (true)"  "then-branch" \
  "$(posh -c 'if [ 5 -gt 3 ]; then echo then-branch; else echo else-branch; fi')"
check "T8b if/else branch (false)" "else-branch" \
  "$(posh -c 'if [ 5 -lt 3 ]; then echo then-branch; else echo else-branch; fi')"

# --- T9: case ---------------------------------------------------------------
check "T9 case match" "two" \
  "$(posh -c 'x=2; case $x in 1) echo one;; 2) echo two;; *) echo other;; esac')"
check "T9b case default" "other" \
  "$(posh -c 'x=z; case $x in 1) echo one;; 2) echo two;; *) echo other;; esac')"

# --- T10: for loop -----------------------------------------------------------
check "T10 for loop accumulation" "6" \
  "$(posh -c 's=0; for i in 1 2 3; do s=$((s+i)); done; echo $s')"

# --- T11: script-file mode ---------------------------------------------------
# T11a: explicit `posh script.sh`
cat > "$WORK/script1.sh" <<'EOF'
greet() { echo "hello $1"; }
greet world
for i in a b c; do echo "item-$i"; done
exit 7
EOF
OUT=$(posh "$WORK/script1.sh"); RC=$?
check "T11a script-file mode output" "hello world
item-a
item-b
item-c" "$OUT"
check "T11a script-file mode exit code" "7" "$RC"

# T11b: executable script with `#!/usr/bin/env posh` shebang
cat > "$WORK/script2.sh" <<'EOF'
#!/usr/bin/env posh
echo "shebang-ok $((6*7))"
EOF
chmod +x "$WORK/script2.sh"
check "T11b shebang (#!/usr/bin/env posh) execution" "shebang-ok 42" \
  "$("$WORK/script2.sh" 2>&1)"

rm -rf "$WORK"

echo ""
echo "=== posh test.sh summary: PASS=$PASS FAIL=$FAIL ==="
[ "$FAIL" -eq 0 ]
