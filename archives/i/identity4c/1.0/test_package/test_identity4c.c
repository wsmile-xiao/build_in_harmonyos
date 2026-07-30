/**
 * test_identity4c.c — L1 smoke test for libufpidentity.
 *
 * Tests both the bundled strmap API (actual function calls, R34) and
 * identity4c library linking.
 *
 * Note: strmap API uses 1=success, 0=failure convention.
 * R34: test must exercise actual library API, not just print a string.
 */
#include <stdio.h>
#include <string.h>
#include "strmap.h"
#include "identity.h"

int main(void)
{
    int passed = 0;
    int total = 3;

    /* ── Test 1: strmap — sm_new / sm_put / sm_get / sm_exists / sm_delete ── */
    StrMap *sm = sm_new(16);
    if (sm == NULL) {
        fprintf(stderr, "FAIL: sm_new returned NULL\n");
        return 1;
    }

    int rc = sm_put(sm, "test_key", "test_value");
    if (rc != 1) {  /* sm_put returns 1 on success */
        fprintf(stderr, "FAIL: sm_put returned %d (expected 1)\n", rc);
        sm_delete(sm);
        return 1;
    }

    if (!sm_exists(sm, "test_key")) {
        fprintf(stderr, "FAIL: sm_exists returned 0 for existing key\n");
        sm_delete(sm);
        return 1;
    }

    char val[64] = {0};
    rc = sm_get(sm, "test_key", val, sizeof(val));
    if (rc != 1 || strcmp(val, "test_value") != 0) {
        fprintf(stderr, "FAIL: sm_get returned %d, val='%s' (expected 1, 'test_value')\n", rc, val);
        sm_delete(sm);
        return 1;
    }

    sm_delete(sm);
    printf("PASS: strmap put/get/exists round-trip OK\n");
    passed++;

    /* ── Test 2: identity4c API type accessibility ── */
    identity_context_t ctx_stub;
    (void)&ctx_stub;
    printf("PASS: identity_context_t type accessible\n");
    passed++;

    /* ── Test 3: identity4c API symbol resolution (link-time check) ── */
    void (*fn1)(identity_context_t*) = &free_identity_context;
    void (*fn2)(authentication_pretext_t*) = &free_authentication_pretext;
    void (*fn3)(authentication_context_t*) = &free_authentication_context;
    (void)fn1; (void)fn2; (void)fn3;
    printf("PASS: library API symbols resolved (link OK)\n");
    passed++;

    printf("\nResults: %d/%d tests passed\n", passed, total);
    return (passed == total) ? 0 : 1;
}
