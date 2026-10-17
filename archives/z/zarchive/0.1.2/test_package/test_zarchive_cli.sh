#!/bin/sh
# Consumer test for the installed zarchive CLI.
#
# Usage: test_zarchive_cli.sh <path-to-installed-zarchive>
#
# Exercises the packaged tool the way a user does: pack a directory into an
# archive, extract it back into a different directory, and compare the
# extracted bytes with the source.  Every step asserts its exit code, and
# the final comparison is byte-exact (cmp).
set -u

CLI=${1:-zarchive}
if [ ! -x "$CLI" ]; then
    echo "not ok - installed CLI is not executable: $CLI"
    exit 1
fi
echo "ok 1 - installed CLI exists and is executable: $CLI"

WORK=cli_work
rm -rf "$WORK"
mkdir -p "$WORK/src/sub"
printf 'zarchive cli payload\n' > "$WORK/src/hello.txt"
# 4 KiB of pattern data so the archive actually compresses
i=0
while [ $i -lt 512 ]; do
    printf 'ABCDEFGH' >> "$WORK/src/sub/pattern.txt"
    i=$((i + 1))
done
printf 'nested\n' > "$WORK/src/sub/deep.txt"

"$CLI" -h >/dev/null 2>&1 || true
"$CLI" > "$WORK/usage.txt" 2>&1 || true
if grep -q "Usage" "$WORK/usage.txt"; then
    echo "ok 2 - no-argument invocation prints usage"
else
    echo "not ok 2 - no-argument invocation prints usage"
    exit 1
fi

if "$CLI" "$WORK/src" "$WORK/out.zar" > "$WORK/pack.log" 2>&1; then
    echo "ok 3 - CLI packs a directory into an archive"
else
    echo "not ok 3 - CLI packs a directory into an archive"
    cat "$WORK/pack.log"
    exit 1
fi

if [ -s "$WORK/out.zar" ]; then
    echo "ok 4 - archive file is non-empty"
else
    echo "not ok 4 - archive file is non-empty"
    exit 1
fi

mkdir -p "$WORK/extracted"
if "$CLI" "$WORK/out.zar" "$WORK/extracted" > "$WORK/extract.log" 2>&1; then
    echo "ok 5 - CLI extracts the archive"
else
    echo "not ok 5 - CLI extracts the archive"
    cat "$WORK/extract.log"
    exit 1
fi

status=0
for rel in hello.txt sub/pattern.txt sub/deep.txt; do
    if cmp -s "$WORK/src/$rel" "$WORK/extracted/$rel"; then
        echo "ok - extracted $rel is byte-identical to the source"
    else
        echo "not ok - extracted $rel differs from the source"
        status=1
    fi
done

if [ $status -eq 0 ]; then
    echo "ok 6 - every extracted file is byte-identical to its source"
else
    echo "not ok 6 - every extracted file is byte-identical to its source"
fi

# Extracting a missing archive must fail rather than produce an empty tree.
if "$CLI" "$WORK/absent.zar" "$WORK/nowhere" >/dev/null 2>&1; then
    echo "not ok 7 - extracting a missing archive fails"
    status=1
else
    echo "ok 7 - extracting a missing archive fails with a non-zero exit code"
fi

rm -rf "$WORK"
exit $status
