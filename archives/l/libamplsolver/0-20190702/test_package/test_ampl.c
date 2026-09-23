/*
 * test_ampl.c — consumer-style test for the packaged libamplsolver.
 *
 * Exercises the real AMPL Solver Library API against the packaged
 * static library:
 *   1. ASL_alloc(ASL_read_pfgh) — allocate an AMPL Solver Interface (ASL)
 *      structure configured for reading .nl files in "pfgh" (presolve +
 *      first/second derivatives + Hessian) mode.
 *   2. Verify the library-initialized fields: ASLtype records the kind
 *      passed to ASL_alloc, n_prob is 1 for an unread model, and the
 *      objective evaluator function pointer (p.Objval) is wired up to a
 *      real library routine (memcpy'd from edagpars_ASL by ASL_alloc).
 *   3. ASL_free(&asl) — release the structure; the library must reset
 *      the caller's pointer to NULL.
 */
#include <stdio.h>
#include "asl.h"

int main(void) {
    ASL *asl;
    int failures = 0;

    /* 1. Allocate an ASL structure (real API, real allocation path). */
    asl = ASL_alloc(ASL_read_pfgh);
    if (!asl) {
        fprintf(stderr, "FAIL: ASL_alloc(ASL_read_pfgh) returned NULL\n");
        return 1;
    }
    printf("ok: ASL_alloc(ASL_read_pfgh) -> %p\n", (void *)asl);

    /* 2a. ASLtype records the requested kind (library-written field). */
    if (asl->i.ASLtype != ASL_read_pfgh) {
        fprintf(stderr, "FAIL: ASLtype = %d, expected %d\n",
                asl->i.ASLtype, ASL_read_pfgh);
        failures++;
    } else {
        printf("ok: ASLtype == ASL_read_pfgh\n");
    }

    /* 2b. n_prob defaults to 1 for an unread model (library-written). */
    if (asl->i.n_prob != 1) {
        fprintf(stderr, "FAIL: n_prob = %d, expected 1\n", asl->i.n_prob);
        failures++;
    } else {
        printf("ok: n_prob == 1\n");
    }

    /* 2c. The objective evaluator is wired to a real library routine. */
    if (asl->p.Objval == NULL) {
        fprintf(stderr, "FAIL: p.Objval function pointer is NULL\n");
        failures++;
    } else {
        printf("ok: p.Objval function pointer is set\n");
    }

    /* 2d. Fresh structure reports an empty model (zeroed i section). */
    if (asl->i.n_var_ != 0 || asl->i.n_con_ != 0) {
        fprintf(stderr, "FAIL: fresh ASL has n_var=%d n_con=%d (expected 0)\n",
                (int)asl->i.n_var_, (int)asl->i.n_con_);
        failures++;
    } else {
        printf("ok: fresh ASL reports 0 vars / 0 cons\n");
    }

    /* 3. Release the structure. ASL_free must NULL the caller pointer. */
    ASL_free(&asl);
    if (asl != NULL) {
        fprintf(stderr, "FAIL: ASL_free did not reset the ASL pointer\n");
        failures++;
    } else {
        printf("ok: ASL_free reset the ASL pointer\n");
    }

    if (failures) {
        fprintf(stderr, "RESULT: %d assertion(s) failed\n", failures);
        return 1;
    }
    printf("RESULT: all libamplsolver checks passed\n");
    return 0;
}
