/*
 * test_cgreen_failpath.c — NEW error-path semantics test for the packaged
 * libcgreen: an intentionally failing suite must be reported by
 * run_test_suite() through a non-zero return code (upstream never isolates
 * this negative contract on a packaged install).
 *
 * Test inventory: 2 intentionally-failing specs (negative path) plus a
 * non-zero-exit verification step; executable itself must exit 0.
 */
#include <cgreen/cgreen.h>
#include <stdio.h>

Describe(CFail);
BeforeEach(CFail) {}
AfterEach(CFail) {}

Ensure(CFail, intentional_failure_one) {
    assert_that(1, is_equal_to(2));
}

Ensure(CFail, intentional_failure_two) {
    assert_that("expected", is_equal_to_string("actual"));
}

int main(void) {
    TestSuite *suite = create_test_suite();
    TestReporter *reporter = create_text_reporter();
    int rc;
    int passes_negative_contract = 0;

    add_test_with_context(suite, CFail, intentional_failure_one);
    add_test_with_context(suite, CFail, intentional_failure_two);
    rc = run_test_suite(suite, reporter);

    /* Error-path contract: a suite with failing assertions must yield a
     * non-zero return code so that CI / build scripts can detect failures. */
    if (rc != 0) {
        printf("test_cgreen_failpath: failing suite correctly reported rc=%d\n", rc);
        passes_negative_contract = 1;
    } else {
        printf("test_cgreen_failpath: ERROR failing suite reported rc=0\n");
    }
    destroy_test_suite(suite);
    destroy_reporter(reporter);
    return passes_negative_contract ? 0 : 1;
}
