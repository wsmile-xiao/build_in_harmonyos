/*
 * test_medianfilter_c.c — consumer of the public C API.
 * Uses only the installed public header MedianFilter.h and links the
 * installed libmedianfilter.a.  Inserts a known 7-sample sequence and
 * checks the median output against the expected value.
 */
#include <MedianFilter.h>
#include <stdio.h>

int main(void)
{
    sMedianFilter_t filter;
    sMedianNode_t buffer[7];
    filter.numNodes = 7;
    filter.medianBuffer = buffer;
    if (MEDIANFILTER_Init(&filter) != 0) {
        fprintf(stderr, "FAIL: MEDIANFILTER_Init\n");
        return 1;
    }
    /* samples: 10,20,30,40,50 -> median of 7-window */
    int in[7] = {10, 20, 30, 40, 50, 60, 70};
    int expected = 40; /* median of 10..70 = 40 */
    int got = 0;
    for (int i = 0; i < 7; i++) {
        got = MEDIANFILTER_Insert(&filter, in[i]);
    }
    if (got != expected) {
        fprintf(stderr, "FAIL: got=%d expected=%d\n", got, expected);
        return 1;
    }
    printf("PASS: C API median=%d\n", got);
    return 0;
}
