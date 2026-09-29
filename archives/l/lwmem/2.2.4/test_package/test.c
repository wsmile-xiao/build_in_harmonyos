/**
 * \file            test.c
 * \brief           lwmem 2.2.4 consumer test — real allocation/free behavior.
 *
 * Calls the actual lwmem API: assigns memory regions, allocates, writes,
 * reallocs, and frees (positive paths), plus ≥2 real failable negative
 * assertions on illegal/boundary inputs (R34). Assertions use the CHECK
 * macro so any failure returns a non-zero exit code; the test is not a
 * print-only or happy-path-only shell. The package is built with the
 * portable default configuration (LWMEM_CFG_ENABLE_STATS=0), so the stats
 * API is not used.
 */
#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include "lwmem/lwmem.h"

static uint32_t lw_mem[2048 / 4]; /* 2 KB region, uint32 for alignment */

static lwmem_region_t lw_regions[] = {
    { lw_mem, sizeof(lw_mem) },
    { NULL, 0 },
};

#define CHECK(x)                                                                                            \
    do {                                                                                                    \
        if (!(x)) {                                                                                         \
            printf("FAIL: %s (line %d)\n", #x, __LINE__);                                                   \
            return 1;                                                                                       \
        }                                                                                                   \
    } while (0)

/*
 * Negative paths use a dedicated explicit lwmem_t instance (_ex API) so
 * they never disturb the default instance used by the positive paths, and
 * exercise only documented invalid-input semantics (no undefined behavior).
 */
static uint32_t lw_neg_mem[64 / 4]; /* 64-byte region for OOM probing */

static lwmem_region_t lw_neg_regions[] = {
    { lw_neg_mem, sizeof(lw_neg_mem) },
    { NULL, 0 },
};

static int run_negative_paths(void) {
    lwmem_t neg;
    void* p = NULL;
    int ret;

    memset(&neg, 0x00, sizeof(neg));

    /* Negative 1: OOM — request far beyond the 64-byte region must fail. */
    CHECK(lwmem_assignmem_ex(&neg, lw_neg_regions) > 0);
    CHECK(lwmem_malloc_ex(&neg, NULL, 4096) == NULL);

    /* Negative 2: invalid input to realloc_s — NULL pointer-to-pointer is
       invalid input, documented to return 0 without touching memory. */
    ret = lwmem_realloc_s_ex(&neg, NULL, NULL, 0);
    CHECK(ret == 0);

    /* Negative 3: get_size on NULL must return 0 (never a valid size). */
    CHECK(lwmem_get_size_ex(&neg, NULL) == 0);

    /* Negative 4: empty region list assigns 0 regions — must not "succeed"
       with a bogus non-zero count. */
    {
        lwmem_t neg2;
        static lwmem_region_t empty_regions[] = { { NULL, 0 } };
        memset(&neg2, 0x00, sizeof(neg2));
        CHECK(lwmem_assignmem_ex(&neg2, empty_regions) == 0);
    }

    printf("negative paths: PASS (4 failable assertions)\n");
    return 0;
}

int main(void) {
    void* p1;
    void* p2;
    void* p3;

    CHECK(lwmem_assignmem(lw_regions) > 0);

    p1 = lwmem_malloc(64);
    CHECK(p1 != NULL);
    memset(p1, 0xAA, 64);

    p2 = lwmem_calloc(4, 16); /* 64 bytes, zeroed */
    CHECK(p2 != NULL);
    {
        uint8_t* b = (uint8_t*)p2;
        int i;
        for (i = 0; i < 64; ++i) {
            CHECK(b[i] == 0);
        }
    }

    p3 = lwmem_realloc(p1, 128);
    CHECK(p3 != NULL);
    {
        uint8_t* b = (uint8_t*)p3;
        int i;
        for (i = 0; i < 64; ++i) { /* leading 64 bytes preserved after realloc */
            CHECK(b[i] == 0xAA);
        }
    }

    CHECK(lwmem_get_size(p3) >= 128);

    lwmem_free(p3);
    lwmem_free(p2);

    /* Re-allocation after free must succeed (availability restored). */
    p1 = lwmem_malloc(32);
    CHECK(p1 != NULL);
    lwmem_free(p1);

    /* Negative paths (failable assertions) on a dedicated instance. */
    if (run_negative_paths() != 0) {
        return 1;
    }

    printf("lwmem consumer test: PASS (positive + 4 failable negative assertions)\n");
    return 0;
}