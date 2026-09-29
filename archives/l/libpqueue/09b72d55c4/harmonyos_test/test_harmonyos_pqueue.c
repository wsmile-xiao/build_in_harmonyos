/*
 * HarmonyOS-specific consumer test for libpqueue 09b72d55c4.
 *
 * Independent entry: own source file + own build/run command, NOT part of
 * test_package (it never runs inside `conan create` / test_package).
 *
 * What it verifies on OHOS (HongMeng Kernel, aarch64, clang15
 * aarch64-unknown-linux-ohos):
 *   - the shipped static library libpqueue.a exports the public API and
 *     links/executes correctly in the OHOS toolchain/runtime;
 *   - priority-queue semantics match upstream: peek returns the highest
 *     priority, pop drains in priority-descending order [8,7,6,5,4] after
 *     two change_priority() calls;
 *   - pqueue_is_valid() still holds (binary heap invariant) after priority
 *     changes;
 *   - the binary runs from a writable $TMPDIR workdir, i.e. it does not
 *     depend on /tmp being writable (OHOS platform constraint).
 *
 * Fail-ability hook: environment variable PQUEUE_TEST_INJECT_POP0=<pri>
 * overrides the expected priority of the first pop. Injecting an impossible
 * value (e.g. 999) makes the assertion fail with a non-zero exit code and a
 * printed failure line -- used as the negative proof, then unset to restore
 * the passing run.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "pqueue.h"

typedef struct node_t
{
    pqueue_pri_t pri;
    int    val;
    size_t pos;
} node_t;

static int
cmp_pri(pqueue_pri_t next, pqueue_pri_t curr)
{
    return (next < curr);
}

static pqueue_pri_t
get_pri(void *a)
{
    return ((node_t *) a)->pri;
}

static void
set_pri(void *a, pqueue_pri_t pri)
{
    ((node_t *) a)->pri = pri;
}

static size_t
get_pos(void *a)
{
    return ((node_t *) a)->pos;
}

static void
set_pos(void *a, size_t pos)
{
    ((node_t *) a)->pos = pos;
}

static int assertions_run = 0;

#define CHECK(cond, fmt, ...)                                           \
    do {                                                                \
        assertions_run++;                                               \
        if (!(cond)) {                                                  \
            fprintf(stderr, "ASSERT FAIL: " fmt "\n", ##__VA_ARGS__);   \
            return 1;                                                   \
        }                                                               \
    } while (0)

int
main(void)
{
    const char *inject = getenv("PQUEUE_TEST_INJECT_POP0");
    pqueue_pri_t inject_pop0 = 0;
    node_t   *ns;
    pqueue_t *pq;
    node_t   *n;
    int       i;

    if (inject) {
        inject_pop0 = (pqueue_pri_t) strtoull(inject, NULL, 10);
    }

    ns = malloc(10 * sizeof(node_t));
    pq = pqueue_init(10, cmp_pri, get_pri, set_pri, get_pos, set_pos);
    CHECK(ns && pq, "pqueue_init returned NULL");

    ns[0].pri = 5; ns[0].val = -5;
    CHECK(pqueue_insert(pq, &ns[0]) == 0, "insert[0] failed");
    ns[1].pri = 4; ns[1].val = -4;
    CHECK(pqueue_insert(pq, &ns[1]) == 0, "insert[1] failed");
    ns[2].pri = 2; ns[2].val = -2;
    CHECK(pqueue_insert(pq, &ns[2]) == 0, "insert[2] failed");
    ns[3].pri = 6; ns[3].val = -6;
    CHECK(pqueue_insert(pq, &ns[3]) == 0, "insert[3] failed");
    ns[4].pri = 1; ns[4].val = -1;
    CHECK(pqueue_insert(pq, &ns[4]) == 0, "insert[4] failed");

    CHECK(pqueue_size(pq) == 5, "size after 5 inserts = %zu, expected 5",
          pqueue_size(pq));

    n = pqueue_peek(pq);
    CHECK(n != NULL, "pqueue_peek returned NULL on non-empty queue");
    CHECK(n->pri == 6 && n->val == -6,
          "peek = pri %llu val %d, expected pri 6 val -6", n->pri, n->val);
    printf("peek: %llu [%d]\n", n->pri, n->val);

    /* raise ns[4] (1 -> 8) and ns[2] (2 -> 7): expected drain 8,7,6,5,4 */
    pqueue_change_priority(pq, 8, &ns[4]);
    pqueue_change_priority(pq, 7, &ns[2]);

    CHECK(pqueue_is_valid(pq) != 0,
          "pqueue_is_valid == 0 after change_priority (heap invariant broken)");

    {
        struct { pqueue_pri_t pri; int val; } expected[5] = {
            { 8, -1 }, { 7, -2 }, { 6, -6 }, { 5, -5 }, { 4, -4 }
        };
        i = 0;
        if (inject) {
            expected[0].pri = inject_pop0;
        }
        while ((n = pqueue_pop(pq))) {
            printf("pop: %llu [%d]\n", n->pri, n->val);
            CHECK(n->pri == expected[i].pri,
                  "pop[%d] pri = %llu, expected %llu",
                  i, n->pri, expected[i].pri);
            CHECK(n->val == expected[i].val,
                  "pop[%d] val = %d, expected %d",
                  i, n->val, expected[i].val);
            i++;
        }
        CHECK(i == 5, "pop count = %d, expected 5", i);
    }

    CHECK(pqueue_size(pq) == 0, "size after drain = %zu, expected 0",
          pqueue_size(pq));
    CHECK(pqueue_peek(pq) == NULL, "pqueue_peek not NULL on empty queue");

    pqueue_free(pq);
    free(ns);

    printf("harmonyos test libpqueue 09b72d55c4: PASS (assertions run: %d)\n",
           assertions_run);
    return 0;
}
