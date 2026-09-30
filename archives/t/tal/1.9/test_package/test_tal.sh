#!/usr/bin/env bash
#--------------------------------------------------------------------
# Consumer test for tal 1.9 - runs the packaged bin/tal.
#
# Usage: bash test_tal.sh <path-to-packaged-tal>
#
# The "upstream exN" cases are the input / command / output examples
# published on the upstream examples page
#   https://thomasjensen.com/software/tal/examples.html
# (upstream ships no automated test suite) and must match byte for byte.
# The remaining cases cover 1.9 behaviour documented in tal.1 / tal.c.
#--------------------------------------------------------------------
set -euo pipefail

TAL="${1:?usage: test_tal.sh <path-to-packaged-tal>}"

if [ ! -x "$TAL" ]; then
    echo "FAIL: packaged tal binary missing or not executable: $TAL"
    exit 1
fi

# The package ships a static-pie AArch64 executable: run it natively on
# AArch64, through qemu user mode anywhere else. A missing emulator is a
# failure, never a silent skip.
case "$(uname -m)" in
    aarch64|arm64)
        run_tal() { "$TAL" "$@"; }
        ;;
    *)
        QEMU="$(command -v qemu-aarch64 || true)"
        if [ -z "$QEMU" ]; then
            echo "FAIL: qemu-aarch64 is required to run the AArch64 package on $(uname -m)"
            exit 1
        fi
        run_tal() { "$QEMU" "$TAL" "$@"; }
        ;;
esac

# Plain mkdir instead of mktemp -d: a 0700 temp dir is not writable on
# HMDFS (UID mapping, knowledge base E011).
work="${TMPDIR:-${HOME:-.}/tmp}/tal-test.$$"
rm -rf "$work"
mkdir -p "$work"
trap 'rm -rf "$work"' EXIT

pass=0
fail=0
ok() { pass=$((pass + 1)); echo "PASS: $1"; }
bad() { fail=$((fail + 1)); echo "FAIL: $1"; }

# check_example <name> <input> <expected> [tal options...]
check_example() {
    name="$1" input="$2" expected="$3"
    shift 3
    if run_tal "$@" < "$input" > "$work/got" 2> "$work/err" \
            && cmp -s "$expected" "$work/got"; then
        ok "$name"
    else
        bad "$name"
        echo "--- expected"; cat "$expected"
        echo "--- actual"; cat "$work/got" "$work/err"
    fi
}

# 1. -v prints the RCS id of release 1.9
if run_tal -v > "$work/v.txt" && grep -q 'tal.c,v 1.9 ' "$work/v.txt"; then
    ok "tal -v reports release 1.9"
else
    bad "tal -v reports release 1.9"; cat "$work/v.txt"
fi

# 2. -h prints the usage synopsis
if run_tal -h > "$work/h.txt" \
        && grep -qF 'Usage: tal [options] [infile [outfile]]' "$work/h.txt"; then
    ok "tal -h prints usage"
else
    bad "tal -h prints usage"; cat "$work/h.txt"
fi

# upstream ex1: tal
cat > "$work/ex1.in" <<'EOF_TAL'
#define HANDLE_KEYSTROKE                \
    kp = readcmd();                               \
    if ( kp.action == cmAnimInc              \
      || kp.action == cmAnimDec) {                     \
        step = ani_adjust_speed (kp.action); \
    } \
    else { \
      if (kp.action == cmAnimSwDir) { \
        dir_up = !dir_up; \
        turning = TRUE; \
        goto dir_change; \
      } \
      else {                \
        if (!dir_up)                \
          view->vmove(1);                      \
        DELAYSYNC;                            \
        V_Pan (0);             \
        view->display(); \
        writestatusline(); \
        return kp; \
      }     \
    }
EOF_TAL
cat > "$work/ex1.out" <<'EOF_TAL'
#define HANDLE_KEYSTROKE                     \
    kp = readcmd();                          \
    if ( kp.action == cmAnimInc              \
      || kp.action == cmAnimDec) {           \
        step = ani_adjust_speed (kp.action); \
    }                                        \
    else {                                   \
      if (kp.action == cmAnimSwDir) {        \
        dir_up = !dir_up;                    \
        turning = TRUE;                      \
        goto dir_change;                     \
      }                                      \
      else {                                 \
        if (!dir_up)                         \
          view->vmove(1);                    \
        DELAYSYNC;                           \
        V_Pan (0);                           \
        view->display();                     \
        writestatusline();                   \
        return kp;                           \
      }                                      \
    }
EOF_TAL
check_example "upstream ex1 (tal)" "$work/ex1.in" "$work/ex1.out"

# upstream ex2: tal -p 0
cat > "$work/ex2.in" <<'EOF_TAL'
/***************************************************/
/* some text and so on                    */
/*                                                    */
/*       even more text                                   */
/*       foo, bar. bar bar.                   */
/*                                                   */
/***************************************************/
EOF_TAL
cat > "$work/ex2.out" <<'EOF_TAL'
/***************************************************/
/* some text and so on                             */
/*                                                 */
/*       even more text                            */
/*       foo, bar. bar bar.                        */
/*                                                 */
/***************************************************/
EOF_TAL
check_example "upstream ex2 (tal -p 0)" "$work/ex2.in" "$work/ex2.out" -p 0

# upstream ex3: tal -k 40 -c .
cat > "$work/ex3.in" <<'EOF_TAL'
Heading One.
   SubHeading.
   FooBar.
   BarFoo.

Heading Two.
   Salamo.
   BratBrat.
   FettFett.
EOF_TAL
cat > "$work/ex3.out" <<'EOF_TAL'
Heading One.............................
   SubHeading...........................
   FooBar...............................
   BarFoo...............................

Heading Two.............................
   Salamo...............................
   BratBrat.............................
   FettFett.............................
EOF_TAL
check_example "upstream ex3 (tal -k 40 -c .)" "$work/ex3.in" "$work/ex3.out" -k 40 -c .

# upstream ex4: tal -i -p 5
{
    printf '%-45s\n' 'Reshape corporate culture  DONE.'
    printf '%-45s\n' 'Gain substantial market share done.'
    printf '%-45s\n' "Analyze competitor's product Done."
    printf '%s\n' 'Improve shareholder value'
    printf '%s\n' 'Assign more funds to research department  done.'
} > "$work/ex4.in"
cat > "$work/ex4.out" <<'EOF_TAL'
Reshape corporate culture                    DONE.
Gain substantial market share                DONE.
Analyze competitor's product                 DONE.
Improve shareholder value
Assign more funds to research department     DONE.
EOF_TAL
check_example "upstream ex4 (tal -i -p 5)" "$work/ex4.in" "$work/ex4.out" -i -p 5

# upstream ex5: tal -m 28
cat > "$work/ex5.in" <<'EOF_TAL'
<!-- foo1    bar1 -->
<!-- foo2        bar2        -->
<!-- foo3             bar3 -->
<!-- foo4      bar4 -->
EOF_TAL
cat > "$work/ex5.out" <<'EOF_TAL'
<!-- foo1    bar1     -->
<!-- foo2        bar2 -->
<!-- foo3             bar3 -->
<!-- foo4      bar4   -->
EOF_TAL
check_example "upstream ex5 (tal -m 28)" "$work/ex5.in" "$work/ex5.out" -m 28

# upstream ex6.1: tal
cat > "$work/ex6_1.in" <<'EOF_TAL'
/* foo foo foo bar */
/* moo moo moo bar */
/* yabba dabba door */
/* ho ho bar */
/* no bar */
EOF_TAL
cat > "$work/ex6_1.out" <<'EOF_TAL'
/* foo foo foo ba  r */
/* moo moo moo ba  r */
/* yabba dabba doo r */
/* ho ho ba        r */
/* no ba           r */
EOF_TAL
check_example "upstream ex6.1 (tal)" "$work/ex6_1.in" "$work/ex6_1.out"

# upstream ex6.2: tal -l 2
cat > "$work/ex6_2.in" <<'EOF_TAL'
/* foo foo foo bar */
/* moo moo moo bar */
/* yabba dabba door */
/* ho ho bar */
/* no bar */
EOF_TAL
cat > "$work/ex6_2.out" <<'EOF_TAL'
/* foo foo foo bar  */
/* moo moo moo bar  */
/* yabba dabba door */
/* ho ho bar        */
/* no bar           */
EOF_TAL
check_example "upstream ex6.2 (tal -l 2)" "$work/ex6_2.in" "$work/ex6_2.out" -l 2

# upstream ex6.3: tal -l 6
cat > "$work/ex6_3.in" <<'EOF_TAL'
/* foo foo foo bar */
/* moo moo moo bar */
/* yabba dabba door */
/* ho ho bar */
/* no bar */
EOF_TAL
cat > "$work/ex6_3.out" <<'EOF_TAL'
/* foo foo foo ba  r */
/* moo moo moo ba  r */
/* yabba dabba doo r */
/* ho ho ba        r */
/* no ba           r */
EOF_TAL
check_example "upstream ex6.3 (tal -l 6)" "$work/ex6_3.in" "$work/ex6_3.out" -l 6

# upstream ex6.4: tal -l 6 -f
cat > "$work/ex6_4.in" <<'EOF_TAL'
/* foo foo foo bar */
/* moo moo moo bar */
/* yabba dabba door */
/* ho ho bar */
/* no bar */
EOF_TAL
cat > "$work/ex6_4.out" <<'EOF_TAL'
/* foo foo foo bar */
/* moo moo moo bar */
/* yabba dabba door */
/* ho ho       bar */
/* no          bar */
EOF_TAL
check_example "upstream ex6.4 (tal -l 6 -f)" "$work/ex6_4.in" "$work/ex6_4.out" -l 6 -f

# -e: explicit trailer (new in 1.9, disables auto-detection)
cat > "$work/e.in" <<'EOF_TAL'
/* a */
/* bbbbbbb */
/* cc*/
EOF_TAL
cat > "$work/e.out" <<'EOF_TAL'
/* a       */
/* bbbbbbb */
/* cc      */
EOF_TAL
check_example "explicit trailer (-e '*/')" "$work/e.in" "$work/e.out" -e '*/'

# infile / outfile arguments instead of stdin / stdout
printf 'x;\nlonger text;\n' > "$work/f.in"
printf 'x          ;\nlonger text;\n' > "$work/f.exp"
if run_tal -p 0 "$work/f.in" "$work/f.out" > "$work/f.stdout" \
        && cmp -s "$work/f.exp" "$work/f.out" && [ ! -s "$work/f.stdout" ]; then
    ok "infile/outfile arguments"
else
    bad "infile/outfile arguments"
fi

# invalid option value: exit status 1 plus a diagnostic
if run_tal -t 0 < /dev/null > /dev/null 2> "$work/t.err"; then
    bad "invalid tab stop (-t 0) is rejected"
elif grep -qF "'0' is an invalid tab stop distance." "$work/t.err"; then
    ok "invalid tab stop (-t 0) is rejected"
else
    bad "invalid tab stop (-t 0) is rejected"; cat "$work/t.err"
fi

# illegal third file name: diagnostic, and no zero-byte outfile left behind
run_tal "$work/f.in" "$work/third.out" extra > /dev/null 2> "$work/x.err" || true
if grep -qF "illegal parameter -- 'extra'" "$work/x.err" && [ ! -e "$work/third.out" ]; then
    ok "illegal third file name leaves no outfile"
else
    bad "illegal third file name leaves no outfile"; cat "$work/x.err"
fi

echo "TAL_TEST_SUMMARY pass=$pass fail=$fail total=$((pass + fail))"
[ "$fail" -eq 0 ]
