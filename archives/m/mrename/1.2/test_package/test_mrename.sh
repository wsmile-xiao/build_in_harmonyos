#!/usr/bin/env sh
# mrename 1.2 functional test — written in POSIX sh.
#
# usage: test_mrename.sh <mrename-wrapper> <package-folder>
#
# Exercises the packaged CLI end to end: help output, copy mode, move mode,
# filenames containing spaces, the confirmation prompt, argument validation,
# the installed layout, a bulk rename that must touch every file exactly once,
# and (when available) execution under dash to prove the scripts no longer
# rely on bash-only syntax.
set -u

MR="$1"
PKG="$2"
pass=0
fail=0

ck() {
    if [ "$2" = "$3" ]; then
        pass=$((pass + 1))
        echo "  ok   $1"
    else
        fail=$((fail + 1))
        echo "  FAIL $1: expected <$3> got <$2>"
    fi
}

count() {
    ls "$1" | wc -l | tr -d ' '
}

T=$(mktemp -d)
trap 'rm -rf "$T"' EXIT

# 1. help screen
h=$("$MR" -h 2>/dev/null | grep -c "MASS RENAME")
ck "help screen printed" "$([ "$h" -ge 1 ] && echo yes || echo no)" "yes"

# 2-5. copy mode keeps the originals and adds numbered prefixed copies;
# the directory must end with exactly 2 originals + 2 copies (a copy that is
# picked up and copied again would show up as an extra file)
d="$T/copy"
mkdir -p "$d"
(cd "$d" && : > a.txt && : > b.txt)
(cd "$d" && echo yes | "$MR" '*.txt' item -c >/dev/null 2>&1)
ck "copy: original kept" "$([ -f "$d/a.txt" ] && echo yes || echo no)" "yes"
n=$(ls "$d" | grep -c '^item[0-9][0-9]*[ab]\.txt$')
ck "copy: two prefixed copies created" "$n" "2"
ck "copy: counter file cleaned up" \
   "$([ -e "$d/.mrename-c" ] && echo yes || echo no)" "no"
ck "copy: no file copied twice" "$(count "$d")" "4"

# 6-8. move mode renames in place, exactly once
d="$T/move"
mkdir -p "$d"
(cd "$d" && : > c.log)
(cd "$d" && echo yes | "$MR" '*.log' pre -m >/dev/null 2>&1)
ck "move: original removed" "$([ -f "$d/c.log" ] && echo yes || echo no)" "no"
n=$(ls "$d" | grep -c '^pre[0-9][0-9]*c\.log$')
ck "move: renamed file present" "$n" "1"
ck "move: exactly one file left" "$(count "$d")" "1"

# 9. filenames containing spaces survive the rename
d="$T/space"
mkdir -p "$d"
(cd "$d" && : > "my file.txt")
(cd "$d" && echo yes | "$MR" '*.txt' sp -m >/dev/null 2>&1)
n=$(ls "$d" | grep -c '^sp[0-9][0-9]*my file\.txt$')
ck "spaces: filename preserved" "$n" "1"

# 10-11. declining the confirmation aborts without touching anything
d="$T/decline"
mkdir -p "$d"
(cd "$d" && : > k.dat)
(cd "$d" && echo no | "$MR" '*.dat' x -m >/dev/null 2>&1)
rc=$?
ck "decline: exit status 1" "$rc" "1"
ck "decline: file untouched" "$([ -f "$d/k.dat" ] && echo yes || echo no)" "yes"

# 12-13. argument validation
o=$("$MR" '*.txt' p -z 2>&1 | grep -c "wrong third parameter")
ck "invalid mode rejected" "$([ "$o" -ge 1 ] && echo yes || echo no)" "yes"
o=$("$MR" '*.txt' 2>&1 | grep -c "Syntax error")
ck "missing argument rejected" "$([ "$o" -ge 1 ] && echo yes || echo no)" "yes"

# 14. installed layout: helper script shipped under libexec and executable
ck "layout: libexec/mrename/mcpmv executable" \
   "$([ -x "$PKG/libexec/mrename/mcpmv" ] && echo yes || echo no)" "yes"

# 15. portability patches are present in the installed scripts
bashisms=$(grep -c -e '\$\[' -e '== "' "$PKG/libexec/mrename/mrename" \
                                        "$PKG/libexec/mrename/mcpmv" \
           2>/dev/null | awk -F: '{s += $2} END {print s + 0}')
ck "patched: no bash-only syntax left" "$bashisms" "0"

# 16-17. bulk move: every match renamed exactly once. Renaming inside the
# directory that find is still reading lets a streaming find (toybox) visit
# the renamed entry again; large directories expose it on any filesystem.
d="$T/bulk"
mkdir -p "$d"
i=1
while [ "$i" -le 200 ]; do
    : > "$d/f$(printf '%03d' "$i").dat"
    i=$((i + 1))
done
(cd "$d" && echo yes | "$MR" '*.dat' b -m >/dev/null 2>&1)
once=$(ls "$d" | grep -c '^b[0-9][0-9]*f[0-9][0-9][0-9]\.dat$')
twice=$(ls "$d" | grep -c '^b[0-9][0-9]*b[0-9]')
ck "bulk: all 200 files renamed" "$once" "200"
ck "bulk: no file renamed twice" "$twice" "0"

# 18. dash round — strict POSIX shell, the failure mode this port fixes
if command -v dash >/dev/null 2>&1; then
    d="$T/dash"
    mkdir -p "$d"
    (cd "$d" && : > z.bin)
    (cd "$d" && PATH="$PKG/libexec/mrename:$PATH" \
        dash "$PKG/libexec/mrename/mrename" '*.bin' dsh -c >/dev/null 2>&1 <<'EOF'
yes
EOF
    )
    n=$(ls "$d" | grep -c '^dsh[0-9][0-9]*z\.bin$')
    ck "dash: copy works under strict POSIX shell" "$n" "1"
else
    echo "  skip dash round: dash not installed on this runner"
fi

echo "passed=$pass failed=$fail"
[ "$fail" -eq 0 ]
