/* test_roundtrip.c — libbigwig 0.4.8 consumer test (HarmonyOS adaptation).
 *
 * Exercises the library end to end on a local file:
 *   bwInit -> create a bigWig file (header, chromosome list, one interval
 *   block plus one span block) -> close -> reopen -> read every entry back
 *   through the R-tree index and verify chromosome metadata, entry counts,
 *   coordinates and values.
 *
 * Returns 0 only when all checks pass.
 */
#include "bigWig.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define N_EXPECTED 6

static const char *expectedChrom = "1";
static uint32_t expectedStart[N_EXPECTED] = {0, 100, 125, 1000, 2000, 3000};
static uint32_t expectedEnd[N_EXPECTED] = {5, 120, 126, 1050, 2050, 3050};
static float expectedValue[N_EXPECTED] = {0.0f, 1.5f, -200.25f, 7.5f, -3.25f, 42.0f};

static int matchEntry(uint32_t start, uint32_t end, float value, char *seen) {
    int i;
    for(i = 0; i < N_EXPECTED; i++) {
        if(!seen[i] && expectedStart[i] == start && expectedEnd[i] == end
           && expectedValue[i] == value) {
            seen[i] = 1;
            return 1;
        }
    }
    return 0;
}

int main(void) {
    const char *chroms[] = {"1", "2"};
    uint32_t chrLens[] = {1000000, 1500000};
    const char *writeChroms[] = {"1", "1", "1"};
    uint32_t starts[] = {0, 100, 125};
    uint32_t ends[] = {5, 120, 126};
    float values[] = {0.0f, 1.5f, -200.25f};
    uint32_t spanStarts[] = {1000, 2000, 3000};
    float spanValues[] = {7.5f, -3.25f, 42.0f};

    char path[1024];
    const char *tmpdir = getenv("TMPDIR");
    bigWigFile_t *fp = NULL;
    bwOverlappingIntervals_t *ov = NULL;
    char seen[N_EXPECTED] = {0};
    uint32_t i;
    int failures = 0;

    if(bwInit(1 << 17) != 0) {
        fprintf(stderr, "FAIL: bwInit\n");
        return 1;
    }

    snprintf(path, sizeof(path), "%s/libbigwig_test_roundtrip.bw",
             (tmpdir && *tmpdir) ? tmpdir : ".");

    fp = bwOpen(path, NULL, "w");
    if(!fp) {
        fprintf(stderr, "FAIL: bwOpen(%s, \"w\")\n", path);
        bwCleanup();
        return 1;
    }

    if(bwCreateHdr(fp, 10)) {
        fprintf(stderr, "FAIL: bwCreateHdr\n");
        goto error;
    }
    fp->cl = bwCreateChromList(chroms, chrLens, 2);
    if(!fp->cl) {
        fprintf(stderr, "FAIL: bwCreateChromList\n");
        goto error;
    }
    if(bwWriteHdr(fp)) {
        fprintf(stderr, "FAIL: bwWriteHdr\n");
        goto error;
    }
    if(bwAddIntervals(fp, writeChroms, starts, ends, values, 3)) {
        fprintf(stderr, "FAIL: bwAddIntervals\n");
        goto error;
    }
    if(bwAddIntervalSpans(fp, "1", spanStarts, 50, spanValues, 3)) {
        fprintf(stderr, "FAIL: bwAddIntervalSpans\n");
        goto error;
    }
    bwClose(fp);
    fp = NULL;

    /* Reopen and verify the written file. */
    fp = bwOpen(path, NULL, "r");
    if(!fp) {
        fprintf(stderr, "FAIL: bwOpen(%s, \"r\")\n", path);
        goto error;
    }
    if(!fp->cl || fp->cl->nKeys != 2
       || strcmp(fp->cl->chrom[0], "1") != 0
       || fp->cl->len[0] != 1000000
       || strcmp(fp->cl->chrom[1], "2") != 0
       || fp->cl->len[1] != 1500000) {
        fprintf(stderr, "FAIL: chromosome list mismatch after reopen\n");
        goto error;
    }
    if(strcmp(expectedChrom, fp->cl->chrom[0]) != 0) {
        fprintf(stderr, "FAIL: expected chromosome %s\n", expectedChrom);
        goto error;
    }

    ov = bwGetOverlappingIntervals(fp, "1", 0, 1000000);
    if(!ov || ov->l != N_EXPECTED) {
        fprintf(stderr, "FAIL: expected %d overlapping entries, got %u\n",
                N_EXPECTED, ov ? (unsigned) ov->l : 0u);
        goto error;
    }
    for(i = 0; i < ov->l; i++) {
        if(!matchEntry(ov->start[i], ov->end[i], ov->value[i], seen)) {
            fprintf(stderr, "FAIL: unexpected entry %u:%u=%f\n",
                    ov->start[i], ov->end[i], (double) ov->value[i]);
            failures++;
        }
    }
    for(i = 0; i < N_EXPECTED; i++) {
        if(!seen[i]) {
            fprintf(stderr, "FAIL: written entry start=%u end=%u value=%f not read back\n",
                    expectedStart[i], expectedEnd[i], (double) expectedValue[i]);
            failures++;
        }
    }
    if(failures) goto error;

    bwDestroyOverlappingIntervals(ov);
    bwClose(fp);
    remove(path);
    bwCleanup();
    printf("test_roundtrip: all %d entries verified\n", N_EXPECTED);
    return 0;

error:
    if(ov) bwDestroyOverlappingIntervals(ov);
    if(fp) bwClose(fp);
    remove(path);
    bwCleanup();
    return 1;
}
