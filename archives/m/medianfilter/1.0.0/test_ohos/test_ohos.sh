#!/usr/bin/env bash
# HarmonyOS-specific test — medianfilter 1.0.0
#
# Runs on OpenHarmony PC against the FINAL Conan package (static library).
# Independently verifies platform delivery aspects the test_package consumer
# does not cover:
#   H1 package structure: lib/libmedianfilter.a + include/MedianFilter.h +
#      include/MedianFilter.hpp all present
#   H2 archived object is ELF64 Little-Endian AArch64 (llvm-readelf class /
#      data / machine on the extracted object; a readelf failure fails the
#      check closed)
#   H3 no host build paths leaked into the object (strings scan)
#   H4 a real end-to-end consumer compiles from the installed public header,
#      links libmedianfilter.a and RUNS on OHOS, producing the expected
#      median values (window 5 over 1..5 -> 3; alternating sequence median)
#
# Usage: bash test_ohos.sh <package_folder> [readelf_path]
# Test artifacts go to a private temp dir removed on any exit path.

set -euo pipefail

PKG="${1:?usage: test_ohos.sh <package_folder> [readelf_path]}"
RE="${2:-readelf}"

WORK="$(mktemp -d "${TMPDIR:-/tmp}/medianfilter-test-ohos.XXXXXX")"
trap 'rm -rf "$WORK"' EXIT INT TERM

fail=0
checks=0
check() {
    checks=$((checks + 1))
    if [ "$2" = "ok" ]; then
        echo "ok $checks - $1"
    else
        echo "not ok $checks - $1 ($2)"
        fail=$((fail + 1))
    fi
}

# ---- H1: package structure --------------------------------------------
if [ -f "$PKG/lib/libmedianfilter.a" ]; then H1a=ok; else H1a="missing lib/libmedianfilter.a"; fi
check "H1a libmedianfilter.a present" "$H1a"
if [ -f "$PKG/include/MedianFilter.h" ]; then H1b=ok; else H1b="missing include/MedianFilter.h"; fi
check "H1b MedianFilter.h present" "$H1b"
if [ -f "$PKG/include/MedianFilter.hpp" ]; then H1c=ok; else H1c="missing include/MedianFilter.hpp"; fi
check "H1c MedianFilter.hpp present" "$H1c"

# ---- H2: AArch64 ELF64 object inside the archive -----------------------
"$RE" --version >/dev/null 2>&1 || RE="$(command -v llvm-readelf || command -v readelf)"
OBJ="$WORK/MedianFilter.o"
if ar x "$PKG/lib/libmedianfilter.a" "$(ar t "$PKG/lib/libmedianfilter.a" | head -1)" --output="$WORK" 2>/dev/null; then
    mv "$WORK"/*.o "$OBJ" 2>/dev/null || true
fi
if [ -f "$OBJ" ]; then
    class="$("$RE" -h "$OBJ" 2>&1 | awk '/Class:/ {print $2; exit}')"
    data="$("$RE" -h "$OBJ" 2>&1 | awk '/Data:/ {print; exit}')"
    machine="$("$RE" -h "$OBJ" 2>&1 | awk '/Machine:/ {print $2" "$3; exit}')"
    if [ "$class" = "ELF64" ] && echo "$data" | grep -q "little endian" && echo "$machine" | grep -q "AArch64"; then
        check "H2 object is ELF64 LE AArch64 (class=$class data=[$data] machine=[$machine])" ok
    else
        check "H2 object is ELF64 LE AArch64 (class=$class data=[$data] machine=[$machine])" "got class=$class data=$data machine=$machine"
    fi
else
    check "H2 object extraction" "could not extract object from archive"
fi

# ---- H3: no host paths in object ---------------------------------------
if [ -f "$OBJ" ]; then
    host_hits="$(strings "$OBJ" | grep -cE '/storage/Users|/build_in_harmonyos|\.conan2|/data/service/hnp' || true)"
    if [ "$host_hits" -eq 0 ]; then
        check "H3 no host build paths in object" ok
    else
        check "H3 no host build paths in object" "$host_hits host path strings found"
    fi
else
    check "H3 no host build paths in object" "object unavailable"
fi

# ---- H4: end-to-end consumer on OHOS -----------------------------------
cat > "$WORK/consumer.c" <<'EOF'
#include <MedianFilter.h>
#include <stdio.h>

int main(void)
{
    sMedianFilter_t filter;
    sMedianNode_t nodes[5];
    filter.numNodes = 5;
    filter.medianBuffer = nodes;
    if (MEDIANFILTER_Init(&filter) != 0) return 2;

    int in[5] = {1, 2, 3, 4, 5};
    int got = 0;
    for (int i = 0; i < 5; i++) got = MEDIANFILTER_Insert(&filter, in[i]);
    if (got != 3) {
        fprintf(stderr, "median(1..5)=%d expected 3\n", got);
        return 1;
    }
    /* window-3 filtering of a spike sequence: spikes must vanish */
    sMedianFilter_t f2;
    sMedianNode_t n2[3];
    f2.numNodes = 3;
    f2.medianBuffer = n2;
    MEDIANFILTER_Init(&f2);
    int seq[7] = {5, 5, 100, 5, 5, 100, 5};
    int out[7];
    for (int i = 0; i < 7; i++) out[i] = MEDIANFILTER_Insert(&f2, seq[i]);
    /* warmup: window not full yet -> unfilled slots are 0-valued, so
       output[0]=median(0,0,5)=0 and output[1]=median(0,5,5)=5;
       once full (i>=2) every window-3 median must be exactly 5 */
    if (out[0] != 0) {
        fprintf(stderr, "warmup output[0]=%d expected 0\n", out[0]);
        return 1;
    }
    for (int i = 1; i < 7; i++) {
        if (out[i] != 5) {
            fprintf(stderr, "spike output[%d]=%d expected 5\n", i, out[i]);
            return 1;
        }
    }
    printf("median(1..5)=%d, spike-filtered all=5: OHOS consumer OK\n", got);
    return 0;
}
EOF

CC="${CC:-/data/service/hnp/bin/clang}"
if "$CC" -O2 -std=c11 -Wall -Wextra -Werror -I"$PKG/include" \
        "$WORK/consumer.c" "$PKG/lib/libmedianfilter.a" -o "$WORK/consumer.ohos" 2>"$WORK/cc.log"; then
    if "$WORK/consumer.ohos" >"$WORK/run.out" 2>&1; then
        if grep -q "OHOS consumer OK" "$WORK/run.out"; then
            check "H4 consumer compiles, links and runs on OHOS" ok
        else
            check "H4 consumer compiles, links and runs on OHOS" "unexpected output: $(cat "$WORK/run.out")"
        fi
    else
        check "H4 consumer compiles, links and runs on OHOS" "run failed: $(cat "$WORK/run.out")"
    fi
else
    check "H4 consumer compiles, links and runs on OHOS" "compile failed: $(cat "$WORK/cc.log")"
fi

echo "1..$checks"
[ "$fail" -eq 0 ] || exit 1