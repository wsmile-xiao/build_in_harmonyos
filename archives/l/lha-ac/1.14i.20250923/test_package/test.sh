#!/bin/sh
# Consumer test for the packaged lha-ac tool set.
# Usage: test.sh /path/to/installed/bin/lha
#
# Every check inspects files written by the tool instead of feeding program
# output back into the shell parser, so a banner, a listing or a member name
# can never be re-interpreted as shell syntax.
set -u

LHA="$1"
WORK="${PWD}/lha-consumer-test"
total=0
passed=0
failed=0
workflow_total=0
workflow_passed=0
workflow_failed=0

ok() {
    total=$((total + 1))
    passed=$((passed + 1))
    echo "ok   - $1"
}

bad() {
    total=$((total + 1))
    failed=$((failed + 1))
    echo "FAIL - $1"
}

workflow_ok() {
    total=$((total + 1))
    passed=$((passed + 1))
    workflow_total=$((workflow_total + 1))
    workflow_passed=$((workflow_passed + 1))
    echo "consumer-workflow PASS - $1"
}

workflow_bad() {
    total=$((total + 1))
    failed=$((failed + 1))
    workflow_total=$((workflow_total + 1))
    workflow_failed=$((workflow_failed + 1))
    echo "consumer-workflow FAIL - $1"
}

rm -rf "${WORK}"
mkdir -p "${WORK}/payload" "${WORK}/extract"
cd "${WORK}" || exit 1

printf 'lha-ac consumer test payload\nsecond line\n' > payload/plain.txt
i=0
while [ ${i} -lt 40 ]; do
    printf 'line %s of the compressible payload\n' "${i}" >> payload/big.txt
    i=$((i + 1))
done

# 1. tool starts and prints a usage/version banner
"${LHA}" > usage.out 2>&1 || true
if grep -qi 'lha' usage.out; then
    ok "lha runs and prints a usage/version banner"
else
    bad "lha runs and prints a usage/version banner"
fi

# 2. archive a single file
if "${LHA}" a single.lzh payload/plain.txt > /dev/null 2>&1 && [ -s single.lzh ]; then
    ok "lha a creates a non-empty archive"
else
    bad "lha a creates a non-empty archive"
fi

# 3. list the archive and find the stored member
if "${LHA}" l single.lzh > list.out 2>&1 && grep -q 'plain.txt' list.out; then
    ok "archive listing names the member"
else
    bad "archive listing names the member"
fi

# 4. the verbose listing exposes the stored compression level column
if "${LHA}" lv single.lzh > listv.out 2>&1 &&
    grep -q 'plain.txt' listv.out &&
    grep -q 'LV' listv.out; then
    ok "verbose listing reports the stored compression level"
else
    bad "verbose listing reports the stored compression level"
fi

# 5. integrity test of the archive
if "${LHA}" t single.lzh > /dev/null 2>&1; then
    ok "lha t reports a healthy archive"
else
    bad "lha t reports a healthy archive"
fi

# 6. round-trip extraction preserves the payload byte for byte
(cd extract && "${LHA}" x ../single.lzh > /dev/null 2>&1)
if [ -f extract/payload/plain.txt ] &&
    cmp -s payload/plain.txt extract/payload/plain.txt; then
    ok "extracted single file matches the original"
else
    bad "extracted single file matches the original"
fi

# 7. archive several members and list them all
if "${LHA}" a multi.lzh payload/plain.txt payload/big.txt > /dev/null 2>&1; then
    ok "lha a stores multiple members"
else
    bad "lha a stores multiple members"
fi
if "${LHA}" l multi.lzh > multi.out 2>&1 && grep -q 'plain.txt' multi.out; then
    ok "multi-member listing contains plain.txt"
else
    bad "multi-member listing contains plain.txt"
fi
if grep -q 'big.txt' multi.out; then
    ok "multi-member listing contains big.txt"
else
    bad "multi-member listing contains big.txt"
fi

# 8. round-trip the multi-member archive
rm -rf extract && mkdir -p extract
(cd extract && "${LHA}" x ../multi.lzh > /dev/null 2>&1)
if [ -f extract/payload/big.txt ] &&
    cmp -s payload/big.txt extract/payload/big.txt; then
    ok "multi-member extraction matches the original big file"
else
    bad "multi-member extraction matches the original big file"
fi

# 9. deleting a member updates the archive
if "${LHA}" d multi.lzh payload/plain.txt > /dev/null 2>&1; then
    ok "lha d removes a member"
else
    bad "lha d removes a member"
fi
if "${LHA}" l multi.lzh > after.out 2>&1 && ! grep -q 'plain.txt' after.out; then
    ok "deleted member is gone from the listing"
else
    bad "deleted member is gone from the listing"
fi

# 10. validate mode reporting and round-trip preservation
# HarmonyOS HMDFS ignores directory chmod() and reports a fixed mode for
# directories, so the archived mode is whatever the platform reports rather
# than the requested 544. lha restores that mode through mkdir(2) at extraction
# time, which the process umask would mask (2771 & ~022 = 2751) and make the
# comparison below fail for a reason unrelated to lha. Compare with an empty
# umask, exactly like the upstream lha-test18 run inside the recipe build.
umask 0
mkdir -p mode-payload/dir mode-extract
printf 'mode preservation payload\n' > mode-payload/dir/file
chmod 544 mode-payload/dir
chmod 400 mode-payload/dir/file
if "${LHA}" a modes.lzh mode-payload > /dev/null 2>&1; then
    ok "lha a stores a directory tree for mode verification"
else
    bad "lha a stores a directory tree for mode verification"
fi
(cd mode-extract && "${LHA}" x ../modes.lzh > /dev/null 2>&1)
if [ -d mode-extract/mode-payload/dir ] &&
    [ "$(stat -c %a mode-payload/dir)" = "$(stat -c %a mode-extract/mode-payload/dir)" ]; then
    ok "extracted directory mode matches the source mode reported by the platform"
else
    bad "extracted directory mode matches the source mode reported by the platform"
fi
if [ -f mode-extract/mode-payload/dir/file ] &&
    [ "$(stat -c %a mode-payload/dir/file)" = "$(stat -c %a mode-extract/mode-payload/dir/file)" ]; then
    ok "extracted file mode matches the source mode reported by the platform"
else
    bad "extracted file mode matches the source mode reported by the platform"
fi

# 11. Complete consumer end-to-end workflow. This is deliberately kept
# separate from the individual assertions above: it uses only the packaged
# bin/lha for the whole user journey.
rm -rf workflow-src workflow-out workflow.lzh workflow-list.out
mkdir -p workflow-src workflow-out
printf 'consumer workflow alpha\n' > workflow-src/alpha.txt
printf 'consumer workflow beta\n' > workflow-src/beta.txt
if (
    set -e
    "${LHA}" a workflow.lzh workflow-src/alpha.txt workflow-src/beta.txt > /dev/null 2>&1
    "${LHA}" l workflow.lzh > workflow-list.out 2>&1
    grep -q 'alpha.txt' workflow-list.out
    grep -q 'beta.txt' workflow-list.out
    "${LHA}" t workflow.lzh > /dev/null 2>&1
    (cd workflow-out && "${LHA}" x ../workflow.lzh > /dev/null 2>&1)
    cmp -s workflow-src/alpha.txt workflow-out/workflow-src/alpha.txt
    cmp -s workflow-src/beta.txt workflow-out/workflow-src/beta.txt
); then
    workflow_ok "installed bin/lha: archive -> list -> test -> extract -> byte-compare"
else
    workflow_bad "installed bin/lha: archive -> list -> test -> extract -> byte-compare"
fi

printf 'CONSUMER_WORKFLOW_RESULT total=%d passed=%d failed=%d\n' "${workflow_total}" "${workflow_passed}" "${workflow_failed}"
printf 'TEST_PACKAGE_RESULT total=%d passed=%d failed=%d\n' "${total}" "${passed}" "${failed}"
[ "${failed}" -eq 0 ] && [ "${workflow_failed}" -eq 0 ] || exit 1
exit 0
