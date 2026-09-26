#!/bin/sh
# Consumer behaviour test for the packaged ifile binary.
#   $1 = private scratch directory   $2 = package folder (for the man page check)
# Every check exits non-zero on failure, so a green run means the delivered
# binary really trains, really ranks and really locks on this platform.
WORK=$1
PKG=$2
if [ -z "$WORK" ]; then
  echo "usage: test_ifile.sh <scratch-dir> [<package-folder>]" >&2
  exit 2
fi
HOME=$WORK
export HOME
fails=0
say() { printf 'check %s: %s\n' "$1" "$2"; }
fail() { printf 'FAILED check %s (%s)\n' "$1" "$2" >&2; fails=$((fails + 1)); }

say 1 "version banner"
ifile --version > "$WORK/v.out" 2>&1
rc=$?
if [ $rc -ne 0 ]; then
  fail 1 "ifile --version rc=$rc"
elif ! grep -q 'ifile 1.3.9' "$WORK/v.out"; then
  fail 1 "version banner missing: $(cat "$WORK/v.out")"
else
  echo "  ok: $(cat "$WORK/v.out")"
fi

say 2 "help exit code (argp works)"
ifile --help > "$WORK/h.out" 2>&1
rc=$?
if [ $rc -ne 0 ] || ! grep -qi 'usage' "$WORK/h.out"; then
  fail 2 "ifile --help rc=$rc"
fi

say 3 "train a spam folder from stdin"
i=0
for word in viagra casino jackpot; do
  i=$((i + 1))
  printf 'From: s%d@example.com\nTo: me@example.com\nSubject: %s offer today\n\ncheap %s pills bonus win %s discount\n' "$i" "$word" "$word" "$word" > "$WORK/spam$i"
  ifile -i spam < "$WORK/spam$i" > "$WORK/inss$i.out" 2>&1 || fail 3 "insert spam$i: $(tail -1 "$WORK/inss$i.out")"
done

say 4 "train a work folder from stdin"
i=0
for word in kernel makefile conan; do
  i=$((i + 1))
  printf 'From: w%d@example.com\nTo: me@example.com\nSubject: %s review thread\n\nplease review this %s patch for the mm subsystem build\n' "$i" "$word" "$word" > "$WORK/work$i"
  ifile -i work < "$WORK/work$i" > "$WORK/insw$i.out" 2>&1 || fail 4 "insert work$i: $(tail -1 "$WORK/insw$i.out")"
done

say 5 "training wrote the database"
if [ -f "$WORK/.idata" ]; then
  echo "  ok: $WORK/.idata is $(wc -c < "$WORK/.idata") bytes"
else
  fail 5 "no \$HOME/.idata after training"
fi

printf 'From: q@example.com\nTo: me@example.com\nSubject: win cheap viagra casino\n\nviagra casino jackpot bonus pills free discount\n' > "$WORK/q_spam"
printf 'From: r@example.com\nTo: me@example.com\nSubject: kernel makefile build review\n\nreview the makefile so the kernel build targets aarch64 mm subsystem\n' > "$WORK/q_work"

say 6 "a spam-like message ranks spam first"
ifile -q < "$WORK/q_spam" > "$WORK/qs.out" 2>&1
top_s=$(grep -v 'Reading message' "$WORK/qs.out" | grep -v '^---' | head -1 | cut -d' ' -f1)
if [ "$top_s" = "spam" ]; then
  echo "  ok: $(grep -v 'Reading message' "$WORK/qs.out" | grep -v '^---' | tr '\n' ' ')"
else
  fail 6 "spam-like query ranked '$top_s' first: $(cat "$WORK/qs.out")"
fi

say 7 "a work-like message ranks work first"
ifile -q < "$WORK/q_work" > "$WORK/qw.out" 2>&1
top_w=$(grep -v 'Reading message' "$WORK/qw.out" | grep -v '^---' | head -1 | cut -d' ' -f1)
if [ "$top_w" = "work" ]; then
  echo "  ok: $(grep -v 'Reading message' "$WORK/qw.out" | grep -v '^---' | tr '\n' ' ')"
else
  fail 7 "work-like query ranked '$top_w' first: $(cat "$WORK/qw.out")"
fi

say 8 "update path (-u FOLDER)"
ifile -u work < "$WORK/q_work" > "$WORK/uw.out" 2>&1
rc=$?
if [ $rc -ne 0 ]; then
  fail 8 "ifile -u work rc=$rc: $(tail -2 "$WORK/uw.out")"
fi

say 9 "two concurrent jobs share the lock without deadlocking"
ifile -q < "$WORK/q_spam" > "$WORK/c1.out" 2>&1 &
pid1=$!
ifile -q < "$WORK/q_work" > "$WORK/c2.out" 2>&1
rc_seq=$?
wait $pid1
rc_bg=$?
if [ $rc_seq -ne 0 ] || [ $rc_bg -ne 0 ]; then
  fail 9 "concurrent queries rc_bg=$rc_bg rc_serial=$rc_seq"
else
  echo "  ok: both completed (background pid $pid1)"
fi

say 10 "reset path (-r, which goes through system())"
ifile -r > "$WORK/r.out" 2>&1
rc=$?
if [ $rc -ne 0 ]; then
  fail 10 "ifile -r rc=$rc: $(tail -2 "$WORK/r.out")"
elif [ -f "$WORK/.idata" ]; then
  fail 10 "-r reported success but the database is still there"
else
  echo "  ok: database removed"
fi

if [ -n "$PKG" ] && [ ! -f "$PKG/share/man/man1/ifile.1" ]; then
  fail 11 "man page not installed under $PKG/share/man/man1"
else
  say 11 "man page installed"
fi

if [ $fails -ne 0 ]; then
  echo "ifile consumer test: $fails check(s) failed" >&2
  exit 1
fi
echo "ifile consumer test: all checks passed"
