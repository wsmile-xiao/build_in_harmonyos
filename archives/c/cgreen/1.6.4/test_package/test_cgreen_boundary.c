/*
 * test_cgreen_boundary.c — NEW boundary/edge-condition tests for the packaged
 * libcgreen (upstream self-suite does not isolate these on a packaged install;
 * boundary values, empty strings and long buffers added on top of upstream).
 *
 * Test inventory: 3 test functions / 10 assertion calls, all expected-pass.
 */
#include <cgreen/cgreen.h>
#include <limits.h>
#include <stdio.h>
#include <string.h>

Describe(CBoundary);
BeforeEach(CBoundary) {}
AfterEach(CBoundary) {}

Ensure(CBoundary, int_limits) {
    assert_that(INT_MAX, is_equal_to(2147483647));
    assert_that(INT_MIN, is_equal_to(-2147483647 - 1));
    assert_that(0, is_equal_to(0));
}

Ensure(CBoundary, unsigned_char_bounds) {
    assert_that((unsigned char)255, is_equal_to(255));
    assert_that((unsigned char)0, is_equal_to(0));
}

Ensure(CBoundary, string_edges) {
    char long_a[128];
    char long_b[128];
    int i;
    for (i = 0; i < 127; i++) {
        long_a[i] = (char)('a' + (i % 26));
    }
    long_a[127] = '\0';
    memcpy(long_b, long_a, sizeof(long_a));

    assert_that("", is_equal_to_string(""));
    assert_that("a", contains_string("a"));
    assert_that("abc", does_not_contain_string("z"));
    assert_that("abc", contains_string("c"));
    assert_that(long_a, is_equal_to_string(long_b));
}

int main(void) {
    TestSuite *suite = create_test_suite();
    TestReporter *reporter = create_text_reporter();
    int rc;
    add_test_with_context(suite, CBoundary, int_limits);
    add_test_with_context(suite, CBoundary, unsigned_char_bounds);
    add_test_with_context(suite, CBoundary, string_edges);
    rc = run_test_suite(suite, reporter);
    destroy_test_suite(suite);
    destroy_reporter(reporter);
    printf("test_cgreen_boundary rc=%d\n", rc);
    return rc;
}
