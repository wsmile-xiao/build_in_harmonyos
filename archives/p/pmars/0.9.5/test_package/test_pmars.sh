#!/bin/sh
# test_package/test_pmars.sh — consumer-side verification for pmars/0.9.5
#
# Executed by conanfile.py test() through `self.run(..., env="conanrun")`, i.e.
# inside the runtime environment Conan composes for this package and its
# dependencies (that is where ncurses' TERMINFO/TERMINFO_DIRS arrive).
#
# Every check runs the binary by its absolute path inside the freshly built
# package (passed as $1) — never through $PATH — so a same-named binary from
# harmonybrew cannot produce a false pass.
#
# Upstream-authored checks exercised here: the six `;assert` directives that the
# shipped warriors carry (evaluated by the assembler, check 5 below).
# Everything else is consumer-side, and is labelled as such in MANIFEST.yml.

set -u

PMARS="$1"
RES="$2"
WARRIORS="$RES/warriors"

pass=0
fail=0
total=0

check() {
    label="$1"
    shift
    total=$((total + 1))
    if "$@" >/dev/null 2>&1; then
        echo "PASS  $label"
        pass=$((pass + 1))
    else
        echo "FAIL  $label"
        fail=$((fail + 1))
    fi
}

echo "pmars consumer test — binary under test: $PMARS"

# 0) The binary must be the one this recipe produced (guard against a
#    same-named binary elsewhere on the system).
total=$((total + 1))
case "$PMARS" in
    */bin/pmars)
        if [ -x "$PMARS" ]; then
            echo "PASS  00 packaged binary is absolute and executable"
            pass=$((pass + 1))
        else
            echo "FAIL  00 packaged binary is absolute and executable"
            fail=$((fail + 1))
        fi
        ;;
    *)
        echo "FAIL  00 packaged binary is absolute and executable"
        fail=$((fail + 1))
        ;;
esac

# 1) `-Q 1000` makes pmars return PMARSVER as its exit code (upstream comment:
#    "return exitcode based on SWITCH_Q setting, useful mainly in scripts").
#    0.9.5 => PMARSVER 95.
total=$((total + 1))
"$PMARS" -Q 1000 >/dev/null 2>&1
rc=$?
if [ "$rc" -eq 95 ]; then
    echo "PASS  01 version probe (-Q 1000 exit 95 == PMARSVER of 0.9.5)"
    pass=$((pass + 1))
else
    echo "FAIL  01 version probe (-Q 1000 exit $rc, expected 95)"
    fail=$((fail + 1))
fi

# 2) The banner must name the release (second, independent version witness).
total=$((total + 1))
if "$PMARS" -Q 1000 2>&1 | grep -q "pMARS v0.9.5"; then
    echo "PASS  02 banner reports pMARS v0.9.5"
    pass=$((pass + 1))
else
    echo "FAIL  02 banner reports pMARS v0.9.5"
    fail=$((fail + 1))
fi

# 3) `-Q 1002` returns PMARSVER*10 + VARIANT; VARIANT is 2 when a graphical
#    (here: curses) display is compiled in, 0 for SERVER, 1 for no-display.
#    95*10+2 = 952, and an exit code keeps its low 8 bits => 184.
#    This pins "curses variant, X11 variant not built" as the shipped product.
total=$((total + 1))
"$PMARS" -Q 1002 >/dev/null 2>&1
rc=$?
if [ "$rc" -eq 184 ]; then
    echo "PASS  03 variant probe (-Q 1002 exit 184 == 0.9.5 + curses display)"
    pass=$((pass + 1))
else
    echo "FAIL  03 variant probe (-Q 1002 exit $rc, expected 184)"
    fail=$((fail + 1))
fi

# 4) Address width: default build uses 32-bit core addresses (ADDR_T = int).
#    Proves -DSMALLMEM was not accidentally enabled.
total=$((total + 1))
"$PMARS" -Q 1003 >/dev/null 2>&1
rc=$?
if [ "$rc" -eq 4 ]; then
    echo "PASS  04 core address width (-Q 1003 exit 4 == 32-bit ADDR_T)"
    pass=$((pass + 1))
else
    echo "FAIL  04 core address width (-Q 1003 exit $rc, expected 4)"
    fail=$((fail + 1))
fi

# 5) Upstream-authored assertions: each shipped warrior carries one `;assert`
#    directive, evaluated by the assembler during `-A` (assemble-only).
#    A failing directive makes pmars report "Number of errors: 1" and exit 3.
idx=10
for w in "$WARRIORS"/*.red; do
    total=$((total + 1))
    name=$(basename "$w")
    "$PMARS" -A -b "$w" </dev/null >"$name.asm.log" 2>&1
    rc=$?
    if [ "$rc" -eq 0 ] && ! grep -qi "assertion\|Number of errors" "$name.asm.log"; then
        echo "PASS  $idx $name (upstream ;assert satisfied)"
        pass=$((pass + 1))
    else
        echo "FAIL  $idx $name (assemble exit $rc)"
        tail -3 "$name.asm.log"
        fail=$((fail + 1))
    fi
    idx=$((idx + 1))
done

# 6) Real fight through the curses display layer: requires ncurses to resolve
#    a terminfo entry, which only happens when the ncurses requirement was
#    declared run=True (otherwise "cannot initialize terminal type", exit 1).
#    stdin is /dev/null because upstream pauses the finished display on
#    "Press any key" — with no terminal attached wgetch returns ERR at once.
total=$((total + 1))
"$PMARS" -b -r 1 -s 8000 -c 500 "$WARRIORS/sonofvain.red" \
        "$WARRIORS/excalibur.red" </dev/null >fight.log 2>&1
rc=$?
if [ "$rc" -eq 0 ] && grep -q "^Results: " fight.log \
   && ! grep -q "cannot initialize terminal" fight.log; then
    echo "PASS  20 curses fight produced a Results: line"
    pass=$((pass + 1))
else
    echo "FAIL  20 curses fight produced a Results: line (exit $rc)"
    echo "--- fight.log tail:"
    tail -5 fight.log
    fail=$((fail + 1))
fi

# 7) The simulator must reject a warrior whose own assertion does not hold —
#    negative control proving the assembler really evaluates `;assert` instead
#    of ignoring it. Upstream exits 3 on assembly errors.
total=$((total + 1))
printf ';redcode-94\n;name too-long\n;assert 0\nend\n' > negative.red
"$PMARS" -A -b negative.red </dev/null >negative.asm.log 2>&1
rc=$?
if [ "$rc" -eq 3 ] && grep -q "Number of errors: 1" negative.asm.log; then
    echo "PASS  21 false ;assert rejected (exit 3, 1 assembly error)"
    pass=$((pass + 1))
else
    echo "FAIL  21 false ;assert rejected (exit $rc, expected 3)"
    tail -4 negative.asm.log
    fail=$((fail + 1))
fi

echo "SUMMARY: $pass/$total passed, $fail failed"
if [ "$fail" -ne 0 ]; then
    exit 1
fi
exit 0
