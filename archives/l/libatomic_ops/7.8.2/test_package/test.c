#include <stdio.h>
#include <assert.h>

/* Include the library header to verify it's consumable */
#include "atomic_ops.h"
/* Include the GPL library header for malloc/stack APIs */
#include "atomic_ops_malloc.h"

int main(void) {
    /* Test AO_fetch_and_add1: increments by 1 (inline, from header) */
    AO_t val = 0;
    AO_fetch_and_add1(&val);
    assert(val == 1);

    /* Test AO_load / AO_store (inline, from header) */
    AO_t store_val = 42;
    AO_store(&store_val, 99);
    assert(AO_load(&store_val) == 99);

    /* Test AO_test_and_set_acquire / AO_CLEAR (inline, from header) */
    AO_TS_t ts = AO_TS_CLEAR;
    AO_TS_t old_ts = AO_test_and_set_acquire(&ts);
    assert(old_ts == AO_TS_CLEAR);
    assert(ts != AO_TS_CLEAR);
    AO_CLEAR(&ts);
    assert(ts == AO_TS_CLEAR);

    /* Test AO_pause (exported from libatomic_ops.a, R34: real library dependency) */
    AO_pause();

    /* Test AO_malloc / AO_free (exported from libatomic_ops_gpl.a) */
    void *p = AO_malloc(128);
    assert(p != NULL);
    AO_free(p);

    printf("libatomic_ops 7.8.2: all atomic operations tests passed\n");
    return 0;
}
