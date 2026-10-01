/*
 * scanmem_target.c -- memory-scan target for the scanmem test_package.
 *
 * A deliberately dumb, dependency-free process whose heap contains a known
 * sentinel so the test can assert that scanmem actually *finds* a value rather
 * than merely exiting 0. Mirrors the role of upstream's test/memfake.c, but
 * with deterministic contents so the expected value is computable.
 *
 * Usage: scanmem_target [repeat_count]
 * Prints its own PID on stdout, then blocks forever so the parent can scan it.
 *
 * SENTINEL is 0x0BADF00D == 195948557 decimal. Kept in sync with
 * test_scanmem.sh (which recomputes it from the same hex literal).
 */

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

#define SENTINEL 0x0BADF00Du

/* 64 KiB of heap: comfortably above scanmem's minimum chunk size so the scan
 * exercises the chunked scan loop rather than the short-buffer fast path. */
#define BLOCK_BYTES (64u * 1024u)
#define BLOCK_INTS  (BLOCK_BYTES / sizeof(uint32_t))

int main(int argc, char **argv)
{
    unsigned long repeat = 4096;
    uint32_t *block;
    unsigned long i;

    if (argc >= 2) {
        repeat = strtoul(argv[1], NULL, 0);
        if (repeat == 0)
            return 1;
    }

    block = (uint32_t *) calloc(BLOCK_INTS, sizeof(uint32_t));
    if (block == NULL) {
        fprintf(stderr, "scanmem_target: calloc failed\n");
        return 1;
    }

    /* One distinctive value at the very start (so a correct scan reports at
     * least one match) and the sentinel repeated through the rest. */
    block[0] = SENTINEL;
    for (i = 1; i < (unsigned long) BLOCK_INTS; i++)
        block[i] = SENTINEL;

    /* Line-buffer stdout so the PID reaches the test harness immediately. */
    setvbuf(stdout, NULL, _IOLBF, 0);
    printf("%ld\n", (long) getpid());
    fflush(stdout);

    /* Block forever; the parent kills us when the checks are done. */
    for (;;)
        pause();

    /* not reached */
    free(block);
    return 0;
}
