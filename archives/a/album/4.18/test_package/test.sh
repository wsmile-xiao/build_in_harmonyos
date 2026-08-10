#!/bin/sh
# album 4.18 test_package — real functional smoke tests.
# Usage: test.sh <package_folder>
PKG="$1"
ALBUM="$PKG/bin/album"
PASS=0
SKIP=0
FAIL=0
TMPDIR="${HOME}/tmp/album-test-$$"
mkdir -p "$TMPDIR"

echo "== [1/3] album --version =="
if "$ALBUM" --version > "$TMPDIR/version.out" 2>&1; then
    echo "PASS: album --version -> $(head -1 "$TMPDIR/version.out")"
    PASS=$((PASS + 1))
else
    echo "FAIL: album --version exited non-zero"
    cat "$TMPDIR/version.out"
    FAIL=$((FAIL + 1))
fi

echo "== [2/3] album -h (usage) =="
if "$ALBUM" -h > "$TMPDIR/help.out" 2>&1; then
    echo "PASS: album -h exited 0"
    PASS=$((PASS + 1))
else
    echo "FAIL: album -h exited non-zero"
    head -20 "$TMPDIR/help.out"
    FAIL=$((FAIL + 1))
fi

echo "== [3/3] album generation (thumbnail requires ImageMagick convert) =="
if command -v convert >/dev/null 2>&1; then
    # ImageMagick available: generate a real album from a tiny image.
    mkdir -p "$TMPDIR/photos"
    # 1x1 PNG (minimal valid image, embedded).
    printf '\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82' > "$TMPDIR/photos/test.png"
    if "$ALBUM" -no_thumb -o "$TMPDIR/out" "$TMPDIR/photos" > "$TMPDIR/gen.out" 2>&1; then
        if [ -f "$TMPDIR/out/index.html" ]; then
            echo "PASS: album generated index.html"
            PASS=$((PASS + 1))
        else
            echo "FAIL: album ran but index.html missing"
            FAIL=$((FAIL + 1))
        fi
    else
        echo "FAIL: album generation failed"
        cat "$TMPDIR/gen.out"
        FAIL=$((FAIL + 1))
    fi
else
    echo "SKIP: album generation — ImageMagick 'convert' not found in this environment"
    echo "      crash point: album spawns 'identify'/'convert' subprocesses for thumbnails"
    echo "      root cause: ImageMagick is a system-level runtime dependency, not installed on this OHOS CI worker"
    echo "      why not feasible: installing a system native binary is outside the pure-Perl package scope"
    SKIP=$((SKIP + 1))
fi

rm -rf "$TMPDIR"
echo ""
echo "album test_package: PASS=$PASS SKIP=$SKIP FAIL=$FAIL"
[ "$FAIL" -eq 0 ] || exit 1
exit 0
