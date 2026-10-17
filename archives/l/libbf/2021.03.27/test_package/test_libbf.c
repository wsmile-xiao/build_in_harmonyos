#include <math.h>
#include <stdio.h>
#include <stdlib.h>

#include "libbf.h"

static bf_context_t ctx;
static int failures = 0;

/* Upstream contract (bftest.c my_bf_realloc): libbf stores the pointer
   verbatim and calls it on first allocation; NULL segfaults (Signal 11).
   Provide the same realloc wrapper upstream uses. */
static void *libbf_realloc(void *opaque, void *ptr, size_t size)
{
    (void)opaque;
    return realloc(ptr, size);
}

#define CHECK(cond, name)                                             \
    do {                                                              \
        if (cond) {                                                   \
            printf("ok - %s\n", name);                                \
        } else {                                                      \
            printf("not ok - %s\n", name);                            \
            failures++;                                               \
        }                                                             \
    } while (0)

int main(void) {
    double d;

    bf_context_init(&ctx, libbf_realloc, NULL);

    /* 1: integer addition */
    {
        bf_t a, b, r;
        bf_init(&ctx, &a);
        bf_init(&ctx, &b);
        bf_init(&ctx, &r);
        bf_set_si(&a, 1);
        bf_set_si(&b, 2);
        bf_add(&r, &a, &b, 53, BF_RNDN);
        bf_get_float64(&r, &d, BF_RNDN);
        CHECK(d == 3.0, "1 + 2 == 3");
        bf_delete(&a);
        bf_delete(&b);
        bf_delete(&r);
    }

    /* 2: integer multiplication */
    {
        bf_t a, b, r;
        bf_init(&ctx, &a);
        bf_init(&ctx, &b);
        bf_init(&ctx, &r);
        bf_set_si(&a, 6);
        bf_set_si(&b, 7);
        bf_mul(&r, &a, &b, 53, BF_RNDN);
        bf_get_float64(&r, &d, BF_RNDN);
        CHECK(d == 42.0, "6 * 7 == 42");
        bf_delete(&a);
        bf_delete(&b);
        bf_delete(&r);
    }

    /* 3: exact division */
    {
        bf_t a, b, r;
        bf_init(&ctx, &a);
        bf_init(&ctx, &b);
        bf_init(&ctx, &r);
        bf_set_si(&a, 1);
        bf_set_si(&b, 4);
        bf_div(&r, &a, &b, 53, BF_RNDN);
        bf_get_float64(&r, &d, BF_RNDN);
        CHECK(d == 0.25, "1 / 4 == 0.25");
        bf_delete(&a);
        bf_delete(&b);
        bf_delete(&r);
    }

    /* 4: square root against a known constant */
    {
        bf_t a, r;
        bf_init(&ctx, &a);
        bf_init(&ctx, &r);
        bf_set_si(&a, 2);
        bf_sqrt(&r, &a, 113, BF_RNDN);
        bf_get_float64(&r, &d, BF_RNDN);
        CHECK(fabs(d - 1.4142135623730951) < 1e-15, "sqrt(2)");
        bf_delete(&a);
        bf_delete(&r);
    }

    /* 5: decimal string input round-trip */
    {
        bf_t a;
        bf_init(&ctx, &a);
        bf_atof(&a, "2.5", NULL, 10, BF_PREC_INF, BF_RNDN);
        bf_get_float64(&a, &d, BF_RNDN);
        CHECK(d == 2.5, "atof(\"2.5\") == 2.5");
        bf_delete(&a);
    }

    bf_context_end(&ctx);

    if (failures == 0) {
        printf("ALL 5 CHECKS PASSED\n");
        return 0;
    }
    printf("%d CHECK(S) FAILED\n", failures);
    return 1;
}
