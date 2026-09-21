#!/bin/sh
# test_package/test_lr.sh — adaptation regression suite for the packaged lr.
#
# Runs inside the conanrun environment, so PATH already contains the packaged
# bin/ directory.  Upstream lr 1.5.1 ships no tests at all (its Makefile has
# only all/clean/install/FRC targets and the tarball contains no test file), so
# this suite is the behavioural evidence that the port works: every assertion
# executes the *installed* lr against a generated fixture tree and checks real
# output or the documented exit statuses.  Deleting bin/lr makes the suite fail
# (CI L1e sabotages the package's bin/ to prove exactly that).
#
# Style exception (code-style §7/§10, documented in notes.md): no `set -e` —
# several assertions call lr on purpose to observe the documented non-zero exit
# statuses (1 = a top level argument cannot be stat'ed, 2 = usage error), and
# errexit would abort the run instead of recording them.  `set -o pipefail` is
# not POSIX and this script runs under /bin/sh (toybox ash) as well as bash.
set -u

DIR="lr-test.$$"
PKG="${LR_PACKAGE_FOLDER:-}"
if [ -z "$PKG" ]; then
  # Fall back to the directory that provides the `lr` on PATH, so the suite is
  # self-contained and reproducible with a plain `sh test_lr.sh` (the packaged
  # layout is <prefix>/bin/lr + <prefix>/share/...).
  PKG=$(CDPATH= cd -- "$(dirname "$(command -v lr)")/.." && pwd) 2>/dev/null || PKG=unset
fi

cleanup() {
  cd .. 2>/dev/null || true
  rm -rf "$DIR"
}
trap cleanup EXIT INT TERM

mkdir -p "$DIR" || exit 1
cd "$DIR" || exit 1

n_ok=0
n_fail=0
ok()  { printf 'ok - %s\n' "$1"; n_ok=$((n_ok + 1)); }
bad() { printf 'not ok - %s\n' "$1"; n_fail=$((n_fail + 1)); }

ESC=$(printf '\033')

# ---------------------------------------------------------------- fixture ----
mkdir -p sub/deep skipme/inner || exit 1
: > one.txt
: > .hidden.txt
: > "wei rd.txt"
: > sub/two.log
: > sub/deep/three.dat
: > skipme/keep.dat
: > skipme/inner/x
mkdir -p .hidsub/inner || exit 1
: > .hidsub/secret
# 3 x 1024 = 3072 bytes; the size is re-read from the filesystem below so no
# assertion depends on which of the two writers was available.
dd if=/dev/zero of=big.bin bs=1024 count=3 2>/dev/null || head -c 3072 /dev/zero > big.bin
SZ_BIG=$(wc -c < big.bin | tr -d ' ')
# Independent expectation for -lh: lr prints one decimal plus a K suffix.
EXP_H_BIG=$(awk -v n="$SZ_BIG" 'BEGIN{printf "%.1fK", n/1024}')
ln -s nowhere sub/broken
# Independent total entry count (everything find sees below the root; lr adds
# the root itself as "."), used as the non-empty-output precondition in A01.
N_FIND_ALL=$(find . ! -path . | wc -l | tr -d ' ')

# ----------------------------------------------------------------- tests -----
printf '1..43\n'

# A01 — the lr on PATH is the tested package's own binary, and it really emits
#       traversal output (precondition so the equality-style assertions
#       A04/A07/A20/A21/A31/A39/A42 cannot pass vacuously on an empty stream).
if [ -n "$PKG" ] && [ "$PKG" != unset ] \
   && [ "$(CDPATH= cd -- "$(dirname "$(command -v lr)")" && pwd)" = "$PKG/bin" ] \
   && [ "$(lr | wc -l)" = "$((N_FIND_ALL + 1))" ]; then
  ok "PATH resolves lr to the package bin/ and lists all $((N_FIND_ALL + 1)) entries"
else
  bad "PATH resolves lr to the package bin/ and lists all $((N_FIND_ALL + 1)) entries (PKG=$PKG, got $(lr | wc -l))"
fi

# A02 — default traversal is recursive (three levels deep)
if lr | grep -q '^skipme/inner/x$'; then ok "default output traverses recursively"; else bad "default output traverses recursively"; fi

# A03 — the traversal root itself is listed
if lr | grep -q '^\.$'; then ok "the traversal root . is listed"; else bad "the traversal root . is listed"; fi

# A04 — default sort order is by name (equals a byte-wise sort)
if [ "$(lr)" = "$(lr | LC_ALL=C sort)" ]; then ok "default output is sorted by name"; else bad "default output is sorted by name"; fi

# A05 — -d does not descend into directories
if [ "$(lr -d)" = "." ]; then ok "-d lists only the starting point"; else bad "-d lists only the starting point"; fi

# A06 — -1 stops below one level of directories
if lr -1 | grep -q '^sub$' && ! lr -1 | grep -q '^sub/two\.log$'; then ok "-1 does not go below one level"; else bad "-1 does not go below one level"; fi

# A07 — -A hides dot files
if ! lr -A | grep -q 'hidden' && ! lr -A | grep -q '\.hidsub'; then ok "-A hides dot files and does not descend dot directories"; else bad "-A hides dot files and does not descend dot directories"; fi

# A08 — without -A the dot file is listed
if lr | grep -q '^\.hidden\.txt$' && lr | grep -q '^\.hidsub/secret$'; then ok "dot file and dot directory contents are listed without -A"; else bad "dot file and dot directory contents are listed without -A"; fi

# A09 — -t 'type == f' keeps regular files only
if lr -t 'type == f' | grep -q '^one\.txt$' && ! lr -t 'type == f' | grep -q '^sub$'; then ok "-t 'type == f' selects regular files only"; else bad "-t 'type == f' selects regular files only"; fi

# A10 — -t 'type == d' keeps directories only
if lr -t 'type == d' | grep -q '^sub/deep$' && ! lr -t 'type == d' | grep -q '^one\.txt$'; then ok "-t 'type == d' selects directories only"; else bad "-t 'type == d' selects directories only"; fi

# A11 — -e REGEX filters on the basename
if [ "$(lr -e 'log$')" = "sub/two.log" ]; then ok "-e filters by basename regex"; else bad "-e filters by basename regex"; fi

# A12 — glob operator ~~
if [ "$(lr -t 'name ~~ "*.dat"' | LC_ALL=C sort)" = "$(printf 'skipme/keep.dat\nsub/deep/three.dat')" ]; then ok "filter operator ~~ globs names"; else bad "filter operator ~~ globs names"; fi

# A13 — POSIX ERE operator =~ (lr strings take no backslash escapes)
if [ "$(lr -t 'name =~ "log$"')" = "sub/two.log" ]; then ok "filter operator =~ matches POSIX ERE"; else bad "filter operator =~ matches POSIX ERE"; fi

# A14 — case-insensitive equality ===
if [ "$(lr -1 -t 'name === "ONE.TXT"')" = "one.txt" ]; then ok "filter operator === is case insensitive"; else bad "filter operator === is case insensitive"; fi

# A15 — numeric filter on size
if lr -t 'size > 1000' | grep -q '^big\.bin$' && ! lr -t 'size > 1000' | grep -q '^one\.txt$'; then ok "numeric filter 'size > 1000'"; else bad "numeric filter 'size > 1000'"; fi

# A16 — %s reports the stat(2) size in bytes (expected from wc -c)
if [ "$(lr -1 -t 'name == "big.bin"' -f '%s' | tr -d ' ')" = "$SZ_BIG" ]; then ok "%s prints the byte size ($SZ_BIG)"; else bad "%s prints the byte size ($SZ_BIG)"; fi

# A17 — %d reports the path depth
if [ "$(lr -t 'name == "three.dat"' -f '%d' | tr -d ' ')" = "3" ]; then ok "%d prints the path depth"; else bad "%d prints the path depth"; fi

# A18 — %i/%n report an inode number and at least one hard link
if lr -t 'name == "one.txt"' -f '%n %i' | grep -qE '^[[:space:]]*[1-9][0-9]*[[:space:]]+[1-9][0-9]*$'; then ok "%n and %i report links and inode"; else bad "%n and %i report links and inode"; fi

# A19 — %m octal mode round-trips through a mode filter, with a negative control
MODE_BIG=$(lr -1 -t 'name == "big.bin"' -f '%m' | tr -d ' ')
if [ -n "$MODE_BIG" ] && lr -1 -t "mode = $MODE_BIG" | grep -q '^big\.bin$' \
   && ! lr -1 -t 'mode = 000' | grep -q '^big\.bin$'; then
  ok "%m octal mode ($MODE_BIG) round-trips and is discriminating"
else
  bad "%m octal mode ($MODE_BIG) round-trips and is discriminating"
fi

# A20 — -0 separates records with NUL bytes (no newline in the raw stream)
if [ "$(lr -0 -d | wc -l)" = "0" ]; then ok "-0 separates entries with NUL"; else bad "-0 separates entries with NUL"; fi

# A21 — -0 stream converts back to the same entry list
if [ "$(lr -0 | tr '\0' '\n' | LC_ALL=C sort)" = "$(lr | LC_ALL=C sort)" ]; then ok "-0 output holds the same entries"; else bad "-0 output holds the same entries"; fi

# A22 — -F appends the file type indicator
if lr -1 -F | grep -q '^sub/$'; then ok "-F marks directories with /"; else bad "-F marks directories with /"; fi

# A23 — -Q shell-quotes a name containing a space
if lr -1 -Q | grep -q "^'wei rd.txt'$"; then ok "-Q shell-quotes names with spaces"; else bad "-Q shell-quotes names with spaces"; fi

# A24 — -P quotes with \$'...' syntax
if [ "$(lr -1 -P | grep 'wei')" = "\$'wei rd.txt'" ]; then ok "-P uses dollar-quoting"; else bad "-P uses dollar-quoting"; fi

# A25 — -l long format prints an ls-style mode and an ISO 8601 date
if lr -1 -l | grep -qE '^[-d][rwxstS-]{9}[+@ ] .*[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2} '; then ok "-l prints mode and ISO date"; else bad "-l prints mode and ISO date"; fi

# A26 — -h renders the size human readable, checked against an independent value
if [ -n "$EXP_H_BIG" ] && lr -1 -t 'name == "big.bin"' -lh | grep -q "$EXP_H_BIG"; then ok "-h prints the human readable size ($EXP_H_BIG)"; else bad "-h prints the human readable size ($EXP_H_BIG)"; fi

# A27 — -s strips the command line prefix
if lr -1 -s sub | grep -q '^two\.log$' && ! lr -1 -s sub | grep -q '^sub/two\.log$'; then ok "-s strips the argument prefix"; else bad "-s strips the argument prefix"; fi

# A28 — prune stops traversal but still prints the pruned directory
if lr -t 'name = "skipme" ? prune : print' | grep -q '^skipme$' && ! lr -t 'name = "skipme" ? prune : print' | grep -q 'skipme/keep'; then ok "prune keeps the entry but stops descending"; else bad "prune keeps the entry but stops descending"; fi

# A29 — -os sorts smallest first
if [ "$(lr -1 -t 'type == f' -os -f '%s\n' | head -1 | tr -d ' ')" = "0" ]; then ok "-os sorts by increasing size"; else bad "-os sorts by increasing size"; fi

# A30 — -oS sorts largest first (expected from wc -c)
if [ "$(lr -1 -t 'type == f' -oS -f '%s\n' | head -1 | tr -d ' ')" = "$SZ_BIG" ]; then ok "-oS sorts by decreasing size"; else bad "-oS sorts by decreasing size"; fi

# A31 — -U prints during traversal without losing entries
if [ "$(lr -U | wc -l)" = "$(lr | wc -l)" ]; then ok "-U lists the same number of entries"; else bad "-U lists the same number of entries"; fi

# A32 — -D computes directory totals that bound the real byte usage
TOT_ROOT=$(lr -D -t 'depth = 0' -f '%t' | tr -d ' ')
if [ -n "$TOT_ROOT" ] && [ "$TOT_ROOT" -gt 0 ] && [ "$((TOT_ROOT * 1024))" -ge "$SZ_BIG" ]; then
  ok "-D %t root total ($TOT_ROOT KiB) covers the $SZ_BIG byte file"
else
  bad "-D %t root total ($TOT_ROOT KiB) covers the $SZ_BIG byte file"
fi

# A33 — symbolic links are reported as type l
if [ "$(lr -t 'type = l')" = "sub/broken" ]; then ok "symlink reported as type l"; else bad "symlink reported as type l"; fi

# A34 — -L keeps a dangling symlink visible instead of aborting
if lr -L | grep -q '^sub/broken$'; then ok "-L tolerates a dangling symlink"; else bad "-L tolerates a dangling symlink"; fi

# A35 — %Y resolves the mount table, not the numeric device-id fallback
FSTYPE=$(lr -d -f '%Y' | tr -d '[:space:]')
if [ -n "$FSTYPE" ] && [ -n "$(printf %s "$FSTYPE" | tr -d 0-9)" ]; then
  ok "%Y reports a filesystem name ($FSTYPE), not a bare device number"
else
  bad "%Y reports a filesystem name ($FSTYPE), not a bare device number"
fi

# A36 — the special path "-" reads file names from standard input
if [ "$(printf 'one.txt\nsub/two.log\n' | lr -d -)" = "$(printf 'one.txt\nsub/two.log')" ]; then ok "- reads file names from stdin"; else bad "- reads file names from stdin"; fi

# A37 — the package also ships the man page and the zsh completion
if [ -f "$PKG/share/man/man1/lr.1" ] && [ -f "$PKG/share/zsh/site-functions/_lr" ]; then ok "package ships man/lr.1 and the _lr completion (PKG=$PKG)"; else bad "package ships man/lr.1 and the _lr completion (PKG=$PKG)"; fi

# A38 — documented exit statuses and messages
rc_e1=0; lr ./absent-dir-xyz >/dev/null 2>e1.err || rc_e1=$?
rc_e2=0; lr --version >e2.out 2>e2.err || rc_e2=$?
if [ "$rc_e1" = "1" ] && grep -q 'absent-dir-xyz' e1.err \
   && [ "$rc_e2" = "2" ] && [ ! -s e2.out ] && grep -q 'Usage:' e2.err; then
  ok "exit status 1 for a missing path, 2 for a usage error"
else
  bad "exit status 1 for a missing path, 2 for a usage error (got $rc_e1/$rc_e2)"
fi

# A39 — -W sorts by name while printing during traversal
if [ "$(lr -W)" = "$(lr)" ]; then ok "-W prints during traversal yet keeps name order"; else bad "-W prints during traversal yet keeps name order"; fi

# A40 — -B breadth-first traversal does not lose entries
if [ "$(lr -B | wc -l)" = "$(lr | wc -l)" ] && lr -B | grep -q '^skipme/inner/x$'; then ok "-B lists the same entries breadth first"; else bad "-B lists the same entries breadth first"; fi

# A41 — depth attribute filter, count cross-checked with find(1) right here
#       (recounted, because earlier assertions leave their own files behind)
N_LEVEL1=$(find . -maxdepth 1 ! -path . | wc -l | tr -d ' ')
if [ "$(lr -t 'depth = 1' | wc -l)" = "$N_LEVEL1" ] && ! lr -t 'depth = 1' | grep -q '/'; then
  ok "-t 'depth = 1' selects exactly the $N_LEVEL1 top level entries"
else
  bad "-t 'depth = 1' selects exactly the $N_LEVEL1 top level entries"
fi

# A42 — $NO_COLOR suppresses the forced color output
if ! NO_COLOR=1 lr -1 -GG 2>/dev/null | grep -q "$ESC"; then ok "NO_COLOR disables color even with -GG"; else bad "NO_COLOR disables color even with -GG"; fi
# A43 must not inherit a host-wide NO_COLOR, otherwise the control would fail spuriously.

# A43 — -GG forces ANSI escapes (control for A42)
if env -u NO_COLOR lr -1 -GG 2>/dev/null | grep -q "$ESC"; then ok "-GG forces colorized output (no inherited NO_COLOR)"; else bad "-GG forces colorized output (no inherited NO_COLOR)"; fi

printf '# lr functional assertions: pass=%s fail=%s total=%s\n' "$n_ok" "$n_fail" $((n_ok + n_fail))
[ "$n_fail" -eq 0 ]
