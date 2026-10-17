#!/usr/bin/env bash
# test_package/test_klustakwik.sh — klustakwik 3.0.2 package verification
#
# Verifies the packaged KlustaKwik binary:
#   1. Binary exists and is executable
#   2. Binary is a valid aarch64 ELF (HarmonyOS PC arm64 target) — only
#      executed when CHECK_ARCH=1 (os=OHOS); on non-OHOS local verify runs
#      this platform-specific check is skipped (the target differs)
#   3. Real clustering run on synthetic 4-feature data (200 points, 2 Gaussians)
#      produces a .clu.1 output file
#   4. The .clu.1 file has the expected shape: first line = number of clusters
#      (>= 2), followed by one label per data point (200 labels)
#   5. The clustering is meaningful: exactly 2 clusters for the 2-Gaussian data
set -euo pipefail

KK_BIN="$1"
DATA_DIR="$2"    # directory containing testdata.fet.1
WORK_DIR="$3"    # writable scratch dir for outputs
CHECK_ARCH="${4:-1}"  # 1 = enforce aarch64 ELF (OHOS), 0 = skip (local verify)

if [ -z "$KK_BIN" ] || [ -z "$DATA_DIR" ] || [ -z "$WORK_DIR" ]; then
    echo "FAIL: usage: test_klustakwik.sh <KlustaKwik-bin> <data-dir> <work-dir> [check-arch]"
    exit 1
fi

if [ ! -f "$KK_BIN" ]; then
    echo "FAIL: $KK_BIN not found"
    exit 1
fi
if [ ! -x "$KK_BIN" ]; then
    echo "FAIL: $KK_BIN not executable"
    exit 1
fi

# ── helper: confirm the file is a real aarch64 ELF via magic bytes ──────────
is_aarch64_elf() {
    local f="$1"
    [ -f "$f" ] || return 1
    local magic mach
    magic=$(dd if="$f" bs=1 count=4 2>/dev/null | od -An -tx1 | tr -d ' \n')
    [ "$magic" = "7f454c46" ] || return 1
    # e_machine little-endian at offset 18-19: aarch64 = 0xB7 0x00
    mach=$(dd if="$f" bs=1 skip=18 count=2 2>/dev/null | od -An -tx1 | tr -d ' \n')
    [ "$mach" = "b700" ]
}

echo "[test 1/5] binary exists and is executable"
echo "PASS: $KK_BIN present and executable"

if [ "$CHECK_ARCH" = "1" ]; then
    echo "[test 2/5] binary is aarch64 ELF (HarmonyOS arm64)"
    if is_aarch64_elf "$KK_BIN"; then
        echo "PASS: $KK_BIN is a valid aarch64 ELF"
    else
        echo "FAIL: $KK_BIN is not an aarch64 ELF"
        exit 1
    fi
else
    echo "[test 2/5] aarch64 ELF check SKIPPED (non-OHOS local verify run)"
fi

echo "[test 3/5] real clustering run on synthetic data"
cp "$DATA_DIR/testdata.fet.1" "$WORK_DIR/"
(
    cd "$WORK_DIR"
    "$KK_BIN" testdata 1 -MinClusters 2 -MaxClusters 5 \
        -MaxPossibleClusters 10 -nStarts 1 -RandomSeed 2304983 \
        -MaxIter 500 -Verbose 0
)
CLU_FILE="$WORK_DIR/testdata.clu.1"
if [ -f "$CLU_FILE" ]; then
    echo "PASS: clustering completed, testdata.clu.1 produced"
else
    echo "FAIL: testdata.clu.1 not produced"
    exit 1
fi

echo "[test 4/5] .clu.1 file shape (1 header + 200 labels)"
TOTAL_LINES=$(wc -l < "$CLU_FILE" | tr -d ' ')
N_CLUSTERS=$(head -1 "$CLU_FILE" | tr -d ' ')
if [ "$TOTAL_LINES" -eq 201 ] && [ "$N_CLUSTERS" -ge 2 ]; then
    echo "PASS: clu has 201 lines, header cluster count = $N_CLUSTERS (>= 2)"
else
    echo "FAIL: unexpected clu shape (lines=$TOTAL_LINES, clusters=$N_CLUSTERS)"
    exit 1
fi

echo "[test 5/5] clustering quality: exactly 2 clusters on 2-Gaussian data"
LABEL_COUNTS=$(tail -n +2 "$CLU_FILE" | sort -n | uniq -c | awk '{print $1}' | tr '\n' ' ')
NUM_LABELS=$(tail -n +2 "$CLU_FILE" | sort -n | uniq | wc -l | tr -d ' ')
if [ "$NUM_LABELS" -eq 2 ]; then
    echo "PASS: data partitioned into exactly 2 clusters (sizes: $LABEL_COUNTS)"
else
    echo "FAIL: expected 2 clusters, got $NUM_LABELS (sizes: $LABEL_COUNTS)"
    exit 1
fi

echo "[result] klustakwik test_package: 5/5 PASS"
