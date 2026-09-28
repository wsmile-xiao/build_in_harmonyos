#include <libalgebra.h>
#include <stdio.h>
#include <stdlib.h>

/* R34 consumer test: must actually call the tested library's public API
 * and observe a real result. libalgebra is header-only; we call the
 * public STORM_* stats functions and validate their outputs. */
int main(void) {
    uint64_t data[2] = { 0xFFFFFFFFFFFFFFFFULL, 0x0000000000000000ULL };
    uint64_t expected_popcount = 64ULL;
    uint64_t pc;
    uint64_t inter, uni, diff;
    int rc = 0;

    /* 1) STORM_popcount64 — public API, hardware/builtin popcount path */
    pc = STORM_popcount64(data[0]);
    printf("STORM_popcount64(0xFFFFFFFFFFFFFFFF) = %llu (expect %llu)\n",
           (unsigned long long)pc, (unsigned long long)expected_popcount);
    if (pc != expected_popcount) { fprintf(stderr, "FAIL: popcount\n"); rc = 1; }

    /* 2) STORM_intersect_count / STORM_union_count — public bitwise stats */
    inter = STORM_intersect_count(data, data, 2);
    uni = STORM_union_count(data, data, 2);
    diff = STORM_diff_count(data, data, 2);
    printf("intersect(data,data)=%llu union(data,data)=%llu diff(data,data)=%llu\n",
           (unsigned long long)inter, (unsigned long long)uni,
           (unsigned long long)diff);
    if (inter != expected_popcount || uni != expected_popcount || diff != 0) {
        fprintf(stderr, "FAIL: intersect/union/diff\n"); rc = 1;
    }

    if (rc == 0) {
        printf("libalgebra test_package: OK\n");
    }
    return rc;
}