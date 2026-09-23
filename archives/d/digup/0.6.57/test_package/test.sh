#!/data/service/hnp/bin/bash
# test_package/test.sh — behaviour checks for the packaged digup executable.
#
# Invoked by test_package/conanfile.py inside the conanrun environment, so
# `digup` is the installed bin/digup. Every check drives the real CLI and
# compares exit codes, scan summaries and the exact digest records written to
# the digest file; no check is satisfied by the binary merely starting up.
#
# Exit codes of digup itself are part of the contract:
#   0 = every scanned file matched the digest file
#   1 = changes (new / changed / renamed / deleted) or read errors were found
#   255 = command line usage error

set -u

TMPBASE="${TMPDIR:-$HOME}"
WORK="$TMPBASE/digup-test-$$"
rm -rf "$WORK"
mkdir -p "$WORK/sha256/sub" "$WORK/md5" "$WORK/sha512" "$WORK/sha1dir"
trap 'rm -rf "$WORK"' EXIT

PASSED=0
FAILED=0

check() {
    # $1 description, $2 actual, $3 expected
    if [ "$2" = "$3" ]; then
        PASSED=$((PASSED + 1))
        printf 'ok   %s\n' "$1"
    else
        FAILED=$((FAILED + 1))
        printf 'FAIL %s\n     expected: [%s]\n     actual:   [%s]\n' "$1" "$3" "$2"
    fi
}

printf 'hello world\n' > "$WORK/sha256/a.txt"
printf 'second file\n' > "$WORK/sha256/sub/b.txt"

# ---- 1. reported version -------------------------------------------------
check "digup --version" "$(digup --version)" "digup 0.6.57"

# ---- 2. option surface ---------------------------------------------------
check "help documents the four digest types" \
    "$(digup --help 2>&1 | grep -c 'md5, sha1, sha256 or sha512')" "1"
check "help documents --modify-window" \
    "$(digup --help 2>&1 | grep -c -- '--modify-window=NUM')" "1"

# ---- 3. fresh scan writes a complete sha256 digest file -------------------
cd "$WORK/sha256"
digup -b -u -t sha256 > "$WORK/first.log" 2>&1
check "first scan reports changes" "$?" "1"
check "fresh scan found both files" \
    "$(grep -c -E 'New: 2$' "$WORK/first.log")" "1"
check "a.txt sha256 record" \
    "$(grep -c -E '^a948904f2f0f479b8f8197694b30184b0d2ed1c1cd2a1ec0fb85d299a192a447  a\.txt$' sha256sum.txt)" "1"
check "sub/b.txt sha256 record" \
    "$(grep -c -E '^f957b19529906961933c5c30f8713c500a9bb5d9d0695c40d48c97a26a3594ec  sub/b\.txt$' sha256sum.txt)" "1"
check "digest file holds exactly two records" \
    "$(grep -c -E '^[0-9a-f]{64}  ' sha256sum.txt)" "2"
check "digest file carries the CRC32 trailer" \
    "$(grep -c -E '^#: crc 0x[0-9a-f]+ eof$' sha256sum.txt)" "1"

# ---- 4. rescan verifies the stored digests --------------------------------
digup -b -c > "$WORK/verify.log" 2>&1
check "verification scan exit code" "$?" "0"
check "both files reported as matched" \
    "$(grep -c ' matched\.$' "$WORK/verify.log")" "2"

# ---- 5. contents change is detected --------------------------------------
printf 'appended line\n' >> a.txt
digup -b -c > "$WORK/changed.log" 2>&1
check "changed file detected (exit code)" "$?" "1"
check "changed file reported by name" \
    "$(grep -c '^a\.txt CHANGED\.$' "$WORK/changed.log")" "1"
check "unchanged file still matches" \
    "$(grep -c '^sub/b\.txt matched\.$' "$WORK/changed.log")" "1"

# ---- 6. md5 digest type ---------------------------------------------------
cd "$WORK/md5"
printf 'hello world\n' > a.txt
digup -b -u -t md5 > "$WORK/md5.log" 2>&1
check "md5 scan reports changes" "$?" "1"
check "a.txt md5 record" \
    "$(grep -c -E '^6f5902ac237024bdd0c176cb93063dc4  a\.txt$' md5sum.txt)" "1"

# ---- 7. sha512 digest type ------------------------------------------------
cd "$WORK/sha512"
printf 'hello world\n' > a.txt
digup -b -u -t sha512 > "$WORK/sha512.log" 2>&1
check "sha512 scan reports changes" "$?" "1"
check "a.txt sha512 record" \
    "$(grep -c -E '^db3974a97f2407b7cae1ae637c0030687a11913274d578492558e39c16c017de84eacdc8c62fe34ee4e12b4b1428817f09b6a2760c3f8a664ceae94d2434a593  a\.txt$' sha512sum.txt)" "1"

# ---- 8. sha1 digest type through -d --------------------------------------
printf 'hello world\n' > "$WORK/sha1dir/a.txt"
digup -b -u -t sha1 -d "$WORK/sha1dir" > "$WORK/sha1.log" 2>&1
check "sha1 scan in -d directory reports changes" "$?" "1"
check "sha1 digest written into the -d directory" \
    "$(grep -c -E '^22596363b3de40b06f981fb85d82312e8c0ed511  a\.txt$' "$WORK/sha1dir/sha1sum.txt")" "1"

# ---- 9. usage errors are reported ----------------------------------------
digup --definitely-not-an-option > "$WORK/usage.log" 2>&1
check "unknown option rejected" "$?" "255"

printf '\nHMBS_TEST_SUMMARY discovered=%d passed=%d failed=%d skipped=0\n' \
    "$((PASSED + FAILED))" "$PASSED" "$FAILED"
[ "$FAILED" -eq 0 ]
