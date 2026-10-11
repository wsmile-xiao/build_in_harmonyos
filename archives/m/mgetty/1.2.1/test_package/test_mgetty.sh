#!/usr/bin/env bash
# Consumer test for mgetty 1.2.1: exercise the installed command-line tools.
#
# The G3 checks mirror the byte-exact expectations of the upstream g3/ test
# suite (g3/Makefile:test) so the packaged tools are validated against the same
# contract the project itself asserts.
set -u
BIN="$1"
fails=0

ok()   { echo "ok   - $1"; }
fail() { echo "FAIL - $1" >&2; fails=$((fails + 1)); }
chk()  { if [ "$2" = "$3" ]; then ok "$1 (= $3)"; else fail "$1: got '$2', expected '$3'"; fi; }

# 1) every tool the recipe packages is present and executable
for b in mgetty sendfax newslock g3cat g32pbm pbm2g3 sff2g3 \
         faxspool faxrunq faxq faxrm faxrunqd faxq-helper; do
    if [ -x "$BIN/$b" ]; then ok "installed executable: $b"; else fail "missing executable: $b"; fi
done

tmp="$(mktemp -d "${TMPDIR:-/tmp}/mgetty-consumer.XXXXXX")" || { echo "FAIL: mktemp" >&2; exit 1; }
trap 'rm -rf "$tmp"' EXIT
cd "$tmp" || exit 1

# 2) G3 toolbox — byte counts asserted by upstream g3/Makefile:test
printf 'P1 1 10\n0 0 0 0 0 0 0 0 0 0\n' | "$BIN/pbm2g3" > t.g3
chk "pbm2g3 encodes P1 to G3" "$(wc -c < t.g3 | tr -d ' ')" 47
"$BIN/g3cat" t.g3 > t2.g3
cmp -s t.g3 t2.g3 && ok "g3cat file copy is byte-identical" || fail "g3cat file copy differs"
"$BIN/g3cat" - < t.g3 > t3.g3
cmp -s t.g3 t3.g3 && ok "g3cat stdin copy is byte-identical" || fail "g3cat stdin copy differs"
chk "g3cat -a"           "$("$BIN/g3cat" -a t.g3 | wc -c | tr -d ' ')" 54
chk "g3cat -a -R"        "$("$BIN/g3cat" -a -R t.g3 | wc -c | tr -d ' ')" 42
chk "g3cat -p 5 -a -R"   "$("$BIN/g3cat" -p 5 -a -R t.g3 | wc -c | tr -d ' ')" 52
chk "g3cat -p 10 -a -R"  "$("$BIN/g3cat" -p 10 -a -R t.g3 | wc -c | tr -d ' ')" 102
chk "g3cat -p 100 -a -R" "$("$BIN/g3cat" -p 100 -a -R t.g3 | wc -c | tr -d ' ')" 1002
chk "g3cat -p 100 -a | g3cat -" \
    "$("$BIN/g3cat" -p 100 -a t.g3 | "$BIN/g3cat" - | wc -c | tr -d ' ')" 47
# upstream g3/Makefile:test: "g3cat - <8-white-lines.g3> test.g3" == "g3cat -h 10 test.g3"
printf 'P1 1 8\n0 0 0 0 0 0 0 0\n' | "$BIN/pbm2g3" | "$BIN/g3cat" - t.g3 > t4.g3
"$BIN/g3cat" -h 10 t.g3 > t5.g3
cmp -s t4.g3 t5.g3 && ok "g3cat concat == g3cat -h 10" || fail "g3cat concat/-h 10 differ"

# 3) tools print their usage when misused
if "$BIN/sendfax" -h 2>&1 | grep -qi "usage"; then ok "sendfax prints usage"; else fail "sendfax usage"; fi
if "$BIN/sff2g3" 2>&1 | grep -qi "usage"; then ok "sff2g3 prints usage"; else fail "sff2g3 usage"; fi

if [ "$fails" -ne 0 ]; then
    echo "$fails consumer assertion(s) failed" >&2
    exit 1
fi
echo "all mgetty consumer assertions passed"
