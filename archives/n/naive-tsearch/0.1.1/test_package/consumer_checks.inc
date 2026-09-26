/* Shared behavioural assertions for one packaged flavour of naive-tsearch.
 *
 * The including translation unit must, before this include:
 *   1. include its flavour's <search.h> (package header, verified below by
 *      the guard macro), and
 *   2. define CONSUMER_CHECKS to the entry-point function name.
 *
 * 5 checks per flavour; consumer_main.c sums both flavours (10 total).
 */
#include <stdio.h>

static int consumer_failures;

static int consumer_cmp(const void *a, const void *b)
{
    const int *lhs = (const int *)a;
    const int *rhs = (const int *)b;
    return (*lhs > *rhs) - (*lhs < *rhs);
}

static void consumer_free_noop(void *datum)
{
    (void)datum;
}

static int consumer_walk_visits;

static void consumer_count_nodes(const void *nodep, VISIT which, int depth)
{
    (void)nodep;
    (void)depth;
    if (which == preorder || which == leaf)
        consumer_walk_visits++;
}

static void consumer_check(int ok, const char *desc)
{
    printf("%s - %s\n", ok ? "ok" : "not ok", desc);
    if (!ok)
        consumer_failures++;
}

int CONSUMER_CHECKS(void)
{
    void *root = NULL;
    int keys[5] = {5, 3, 8, 1, 9};
    int absent = 42;
    void *nodes[5];
    void *again;
    size_t i;
    int found_all = 1;

    consumer_failures = 0;

    /* 1. insert 5 keys, then find every node back at its own address */
    for (i = 0; i < sizeof keys / sizeof keys[0]; i++)
        nodes[i] = tsearch(&keys[i], &root, consumer_cmp);
    for (i = 0; i < sizeof keys / sizeof keys[0]; i++) {
        if (nodes[i] == NULL || tfind(&keys[i], &root, consumer_cmp) != nodes[i])
            found_all = 0;
    }
    consumer_check(found_all, "tfind returns all 5 inserted nodes");

    /* 2. inserting an existing key must reuse the existing node */
    again = tsearch(&keys[0], &root, consumer_cmp);
    consumer_check(again == nodes[0], "duplicate tsearch reuses existing node");

    /* 3. lookup of an absent key must miss */
    consumer_check(tfind(&absent, &root, consumer_cmp) == NULL,
                   "tfind on absent key returns NULL");

    /* 4. deleting one key removes only that key */
    tdelete(&keys[4], &root, consumer_cmp);
    consumer_check(
        tfind(&keys[4], &root, consumer_cmp) == NULL
            && tfind(&keys[0], &root, consumer_cmp) == nodes[0]
            && tfind(&keys[1], &root, consumer_cmp) == nodes[1]
            && tfind(&keys[2], &root, consumer_cmp) == nodes[2]
            && tfind(&keys[3], &root, consumer_cmp) == nodes[3],
        "tdelete removes only the deleted key");

    /* 5. twalk visits the 4 remaining nodes exactly once, then tdestroy
          tears the tree down without crashing */
    consumer_walk_visits = 0;
    twalk(root, consumer_count_nodes);
    consumer_check(consumer_walk_visits == 4,
                   "twalk visits the 4 remaining nodes");
    tdestroy(root, consumer_free_noop);

    return consumer_failures;
}
