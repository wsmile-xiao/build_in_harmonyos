/*
 * test_package — tommyds 3.0 consumer test
 *
 * Genuinely exercises the installed package: builds a tommy_hashtable,
 * inserts N objects, searches each by value (all must be found), checks a
 * missing key is NOT found, then removes some elements and re-verifies.
 * Uses the tommy_hashtable API from <tommyds/tommy.h> (R34: not a stub).
 */
#include <stdio.h>
#include <stdlib.h>

#include <tommyds/tommy.h>

typedef struct obj {
    tommy_node node;
    int value;
} obj;

/* tommy_search_func: return 0 (match) if the object value equals *arg */
static int compare(const void* arg, const void* o)
{
    const int* want = (const int*)arg;
    const obj* item = (const obj*)o;
    return item->value != *want;
}

int main(void)
{
    const int N = 1024;
    tommy_hashtable ht;
    obj* objs;
    int i;

    objs = (obj*)malloc(sizeof(obj) * (size_t)N);
    if (!objs) {
        fprintf(stderr, "FAIL: malloc\n");
        return 1;
    }

    tommy_hashtable_init(&ht, 128);

    for (i = 0; i < N; ++i) {
        objs[i].value = i;
        tommy_hashtable_insert(&ht, &objs[i].node, &objs[i],
                               tommy_inthash_u32((tommy_uint32_t)i));
    }

    /* every inserted element must be found */
    for (i = 0; i < N; ++i) {
        obj* found = (obj*)tommy_hashtable_search(
            &ht, compare, &i, tommy_inthash_u32((tommy_uint32_t)i));
        if (!found || found->value != i) {
            fprintf(stderr, "FAIL: element %d not found\n", i);
            return 2;
        }
    }

    /* a missing key must NOT be found */
    {
        int missing = N + 777;
        obj* found = (obj*)tommy_hashtable_search(
            &ht, compare, &missing, tommy_inthash_u32((tommy_uint32_t)missing));
        if (found) {
            fprintf(stderr, "FAIL: unexpected element found\n");
            return 3;
        }
    }

    /* remove every other element and verify it is gone */
    for (i = 0; i < N; i += 2) {
        obj* removed = (obj*)tommy_hashtable_remove(
            &ht, compare, &i, tommy_inthash_u32((tommy_uint32_t)i));
        if (!removed || removed->value != i) {
            fprintf(stderr, "FAIL: element %d not removed\n", i);
            return 4;
        }
    }
    for (i = 0; i < N; i += 2) {
        obj* found = (obj*)tommy_hashtable_search(
            &ht, compare, &i, tommy_inthash_u32((tommy_uint32_t)i));
        if (found) {
            fprintf(stderr, "FAIL: removed element %d still present\n", i);
            return 5;
        }
    }

    tommy_hashtable_done(&ht);
    free(objs);

    printf("tommyds test_package: %d insert + %d search + %d remove OK\n",
           N, N, N / 2);
    return 0;
}
