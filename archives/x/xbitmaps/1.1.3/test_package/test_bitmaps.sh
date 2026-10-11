#!/bin/sh
# test_bitmaps.sh - scan every installed xbitmaps data file and validate it
# with the real X11 bitmap parsing rule: each file must define
# <name>_width / <name>_height and a <name>_bits[] array whose 0x byte
# count equals ((width+7)/8)*height.
#
# Env: XBITMAPS_DIR   - installed include/X11/bitmaps directory
#      XBITMAPS_EXPECT - expected file count (default 71)
set -u

DIR="${XBITMAPS_DIR:?XBITMAPS_DIR not set}"
EXPECT="${XBITMAPS_EXPECT:-71}"

count=0
failed=0

for f in "$DIR"/*; do
    [ -f "$f" ] || continue
    name=$(basename "$f")
    count=$((count + 1))

    # NB: the macro stem may differ from the file name (upstream quirk:
    # "calculator" contains the "icon" bitmap), so take the stem from the
    # first <stem>_width define, exactly like X11's XReadBitmapFile.
    stem=$(sed -n 's/^#define \([A-Za-z0-9_]\{1,\}\)_width[[:space:]]\{1,\}[0-9]\{1,\}.*/\1/p' "$f" | head -n 1)
    if [ -z "$stem" ]; then
        echo "FAIL($name): no <stem>_width define"
        failed=$((failed + 1))
        continue
    fi
    w=$(sed -n "s/^#define ${stem}_width[[:space:]]\{1,\}\([0-9]\{1,\}\).*/\1/p" "$f" | head -n 1)
    h=$(sed -n "s/^#define ${stem}_height[[:space:]]\{1,\}\([0-9]\{1,\}\).*/\1/p" "$f" | head -n 1)
    if [ -z "$w" ] || [ -z "$h" ]; then
        echo "FAIL($name): missing ${stem} width/height defines"
        failed=$((failed + 1))
        continue
    fi

    bytes=$(awk -v n="${stem}_bits" '
        index($0, n "[]") > 0 { inbits = 1 }
        inbits {
            had_end = index($0, "}")
            gsub(/[^0-9a-fA-FxX,]/, "")
            split($0, arr, ",")
            for (i in arr) if (arr[i] ~ /^0x/) total++
            if (had_end) exit
        }
        END { print total + 0 }' "$f")

    want=$((((w + 7) / 8) * h))
    if [ "$bytes" -ne "$want" ]; then
        echo "FAIL($name): $bytes data bytes, want $want (${w}x${h})"
        failed=$((failed + 1))
    fi
done

echo "scanned=$count failed=$failed"

if [ "$count" -ne "$EXPECT" ]; then
    echo "FAIL: expected $EXPECT installed bitmaps, found $count"
    exit 1
fi
if [ "$failed" -ne 0 ]; then
    exit 1
fi
echo "test_bitmaps.sh: ALL PASS"
