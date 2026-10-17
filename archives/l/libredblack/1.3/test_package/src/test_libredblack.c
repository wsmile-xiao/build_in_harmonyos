/* libredblack consumer test.
 *
 * Links the installed libredblack and drives the real public API declared in
 * <redblack.h> (R34: the test must exercise the package under test, not merely
 * link it).
 *
 * The tree stores *pointers* to caller-owned data, so the keys live in a
 * static array here and must outlive the tree.  200 keys are inserted in
 * descending order, which is the worst case for an unbalanced tree — a
 * correct red-black implementation keeps the walk in sorted order regardless.
 */

#include <redblack.h>

#include <stdio.h>

#define NKEYS 200

static int failures = 0;

static void check(int ok, const char *what)
{
    printf("%s %s\n", ok ? "ok  " : "FAIL", what);
    if (!ok) {
        ++failures;
    }
}

static int keys[NKEYS];

static int compare(const void *pa, const void *pb, const void *config)
{
    int a = *(const int *)pa;
    int b = *(const int *)pb;
    (void)config;
    return a < b ? -1 : (a > b ? 1 : 0);
}

static int walk_seen = 0;
static int walk_sorted = 1;
static int walk_prev = 0;

static void visitor(const void *nodep, const VISIT which, const int depth, void *arg)
{
    int value;
    (void)depth;
    (void)arg;
    /* count each node once: rbwalk reports leaf and postorder per node */
    if (which == leaf || which == postorder) {
        value = *(const int *)nodep;
        if (walk_seen > 0 && value <= walk_prev) {
            walk_sorted = 0;
        }
        walk_prev = value;
        ++walk_seen;
    }
}

int main(void)
{
    struct rbtree *rb;
    const void *val;
    int i;
    int missing = 999999;
    int steps;

    rb = rbinit(compare, NULL);
    check(rb != NULL, "rbinit() returned a tree");
    if (rb == NULL) {
        return 1;
    }

    /* insert 200 distinct keys in descending order */
    for (i = 0; i < NKEYS; ++i) {
        keys[i] = NKEYS - i;            /* 200, 199, ... , 1 */
        rbsearch(&keys[i], rb);
    }

    /* 1. an inserted key is findable, and the stored pointer is our own */
    val = rbfind(&keys[0], rb);         /* keys[0] == 200 */
    check(val != NULL && *(const int *)val == NKEYS,
          "rbfind() finds an inserted key and returns the caller's data");

    /* 2. a key that was never inserted is not found */
    val = rbfind(&missing, rb);
    check(val == NULL, "rbfind() returns NULL for an absent key");

    /* 3. the tree knows its own minimum and maximum */
    val = rbmin(rb);
    check(val != NULL && *(const int *)val == 1, "rbmin() is 1");
    val = rbmax(rb);
    check(val != NULL && *(const int *)val == NKEYS, "rbmax() is 200");

    /* 4. walking from the first key yields every key in ascending order */
    steps = 0;
    val = rblookup(RB_LUFIRST, NULL, rb);
    while (val != NULL) {
        if (*(const int *)val != ++steps) {
            break;
        }
        val = rblookup(RB_LUNEXT, val, rb);
    }
    check(steps == NKEYS,
          "RB_LUFIRST/RB_LUNEXT walk visits all 200 keys in ascending order");

    /* 5. range lookups behave as documented */
    {
        int probe = 100;
        val = rblookup(RB_LUGREAT, &probe, rb);
        check(val != NULL && *(const int *)val == 101,
              "RB_LUGREAT from 100 gives 101 (strictly greater)");
        val = rblookup(RB_LULESS, &probe, rb);
        check(val != NULL && *(const int *)val == 99,
              "RB_LULESS from 100 gives 99 (strictly less)");
    }

    /* 6. rbwalk sees every node exactly once, in sorted order */
    walk_seen = 0;
    walk_sorted = 1;
    rbwalk(rb, visitor, NULL);
    check(walk_seen == NKEYS, "rbwalk() visited all 200 nodes");
    check(walk_sorted == 1, "rbwalk() visited them in ascending order");

    /* 7. deletion removes the key from the tree */
    val = rbdelete(&keys[NKEYS - 1], rb);   /* keys[199] == 1 */
    check(rbfind(&keys[NKEYS - 1], rb) == NULL, "rbdelete() removed key 1");
    val = rbmin(rb);
    check(val != NULL && *(const int *)val == 2, "minimum is now 2");
    val = rbdelete(&missing, rb);
    check(val == NULL, "rbdelete() returns NULL for an absent key");

    rbdestroy(rb);

    if (failures != 0) {
        fprintf(stderr, "%d libredblack consumer check(s) FAILED\n", failures);
        return 1;
    }
    printf("all libredblack consumer checks passed\n");
    return 0;
}
