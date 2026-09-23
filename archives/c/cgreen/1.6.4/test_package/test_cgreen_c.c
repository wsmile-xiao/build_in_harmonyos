/*
 * test_cgreen_c.c — NEW consumer closed-loop tests for packaged libcgreen
 * (HarmonyOS PC). Uses the installed library as a regular C consumer:
 * assertion constraints, string helpers, pointer and double checks plus
 * numeric is_true/is_false coverage.
 *
 * Test inventory: 7 test functions / 24 assertion calls, all expected-pass.
 */
#include <cgreen/cgreen.h>
#include <stdint.h>
#include <stdio.h>

Describe(CBasic);
BeforeEach(CBasic) {}
AfterEach(CBasic) {}

Ensure(CBasic, integer_assertions) {
    assert_that(1, is_true);
    assert_that(0, is_false);
    assert_that(2 + 2, is_equal_to(4));
    assert_that(2 + 2, is_not_equal_to(5));
    assert_that(-7, is_equal_to(-7));
}

Ensure(CBasic, truth_table_assertions) {
    assert_that(1 == 1, is_true);
    assert_that(0 == 1, is_false);
    assert_that(!0, is_true);
}

Ensure(CBasic, string_assertions) {
    assert_that("Hello", is_equal_to_string("Hello"));
    assert_that("Hello", is_not_equal_to_string("hello"));
    assert_that("Hello", contains_string("ell"));
    assert_that("cgreen", begins_with_string("cgre"));
    assert_that("cgreen", ends_with_string("reen"));
}

Ensure(CBasic, pointer_assertions) {
    int value = 42;
    int *ptr = &value;
    assert_that(ptr, is_not_null);
    assert_that((void *)NULL, is_null);
    assert_that(*ptr, is_equal_to(42));
}

Ensure(CBasic, double_assertions) {
    assert_that_double(1.5 + 1.5, is_equal_to_double(3.0));
    assert_that_double(-500, is_not_equal_to_double(0));
    assert_that_double(1.0e-300, is_equal_to_double(1.0e-300));
    assert_that_double(4.9406564584124654E-324, is_equal_to_double(4.9406564584124654E-324));
}

Ensure(CBasic, suite_creation_and_destruction) {
    TestSuite *tmp = create_test_suite();
    assert_that(tmp, is_not_null);
    destroy_test_suite(tmp);
    assert_that(1, is_true);
}

Ensure(CBasic, reporter_creation_and_destruction) {
    TestReporter *tmp = create_text_reporter();
    assert_that(tmp, is_not_null);
    destroy_reporter(tmp);
    assert_that(0, is_false);
}

int main(void) {
    TestSuite *suite = create_test_suite();
    TestReporter *reporter = create_text_reporter();
    int rc;
    add_test_with_context(suite, CBasic, integer_assertions);
    add_test_with_context(suite, CBasic, truth_table_assertions);
    add_test_with_context(suite, CBasic, string_assertions);
    add_test_with_context(suite, CBasic, pointer_assertions);
    add_test_with_context(suite, CBasic, double_assertions);
    add_test_with_context(suite, CBasic, suite_creation_and_destruction);
    add_test_with_context(suite, CBasic, reporter_creation_and_destruction);
    rc = run_test_suite(suite, reporter);
    destroy_test_suite(suite);
    destroy_reporter(reporter);
    printf("test_cgreen_c: %d suites ran, rc=%d\n", 1, rc);
    return rc;
}
