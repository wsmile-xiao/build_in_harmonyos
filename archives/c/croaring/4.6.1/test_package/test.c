/* test_package/test.c — consumer test for croaring/4.6.1
 * Uses the roaring bitmap C API to verify the library is usable.
 */
#include <stdio.h>
#include <stdlib.h>
#include "roaring/roaring.h"

int main(void) {
    roaring_bitmap_t *r1 = roaring_bitmap_create();
    if (!r1) {
        fprintf(stderr, "FAIL: roaring_bitmap_create() returned NULL for r1\n");
        return 1;
    }
    roaring_bitmap_add(r1, 100);
    roaring_bitmap_add(r1, 200);
    roaring_bitmap_add(r1, 300);

    roaring_bitmap_t *r2 = roaring_bitmap_create();
    if (!r2) {
        fprintf(stderr, "FAIL: roaring_bitmap_create() returned NULL for r2\n");
        roaring_bitmap_free(r1);
        return 1;
    }
    roaring_bitmap_add(r2, 200);
    roaring_bitmap_add(r2, 300);
    roaring_bitmap_add(r2, 400);

    roaring_bitmap_t *and_result = roaring_bitmap_and(r1, r2);
    if (!and_result) {
        fprintf(stderr, "FAIL: roaring_bitmap_and() returned NULL\n");
        roaring_bitmap_free(r1);
        roaring_bitmap_free(r2);
        return 1;
    }
    uint64_t card = roaring_bitmap_get_cardinality(and_result);
    if (card != 2) {
        fprintf(stderr, "FAIL: intersection cardinality=%llu, expected 2\n",
                (unsigned long long)card);
        roaring_bitmap_free(r1);
        roaring_bitmap_free(r2);
        roaring_bitmap_free(and_result);
        return 1;
    }

    roaring_bitmap_t *or_result = roaring_bitmap_or(r1, r2);
    if (!or_result) {
        fprintf(stderr, "FAIL: roaring_bitmap_or() returned NULL\n");
        roaring_bitmap_free(r1);
        roaring_bitmap_free(r2);
        roaring_bitmap_free(and_result);
        return 1;
    }
    card = roaring_bitmap_get_cardinality(or_result);
    if (card != 4) {
        fprintf(stderr, "FAIL: union cardinality=%llu, expected 4\n",
                (unsigned long long)card);
        roaring_bitmap_free(r1);
        roaring_bitmap_free(r2);
        roaring_bitmap_free(and_result);
        roaring_bitmap_free(or_result);
        return 1;
    }

    printf("test croaring 4.6.1: OK (and=%llu, or=%llu)\n",
           (unsigned long long)roaring_bitmap_get_cardinality(and_result),
           (unsigned long long)roaring_bitmap_get_cardinality(or_result));

    roaring_bitmap_free(r1);
    roaring_bitmap_free(r2);
    roaring_bitmap_free(and_result);
    roaring_bitmap_free(or_result);
    return 0;
}
