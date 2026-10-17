/* test.c — easy_memory 0.7.0 consumer smoke test (R34: 真实调用被测包 API) */
#define EASY_MEMORY_IMPLEMENTATION
#include "easy_memory.h"

#include <stdio.h>
#include <string.h>

int main(void) {
    EM *em = em_create(4096);
    if (em == NULL) {
        fprintf(stderr, "FAIL: em_create returned NULL\n");
        return 1;
    }

    void *p1 = em_alloc(em, 64);
    if (p1 == NULL) {
        fprintf(stderr, "FAIL: em_alloc returned NULL\n");
        em_destroy(em);
        return 1;
    }
    memset(p1, 0xAB, 64);

    void *p2 = em_alloc_aligned(em, 128, 64);
    if (p2 == NULL) {
        fprintf(stderr, "FAIL: em_alloc_aligned returned NULL\n");
        em_destroy(em);
        return 1;
    }
    if (((size_t)p2 & 63u) != 0) {
        fprintf(stderr, "FAIL: em_alloc_aligned misaligned\n");
        em_destroy(em);
        return 1;
    }
    memset(p2, 0xCD, 128);

    em_free(p1);
    em_free(p2);
    em_destroy(em);

    printf("easy_memory smoke test PASSED\n");
    return 0;
}
