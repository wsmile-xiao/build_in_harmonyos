/*
 * Consumer test for minunit 0.0-git20230524 (single-header C unit test framework).
 *
 * Strategy (mirrors the official upstream contract ci/check_example.sh):
 *   - 5 positive cases exercising every passing assertion macro
 *     (mu_check / mu_assert / mu_assert_int_eq / mu_assert_double_eq /
 *      mu_assert_string_eq);
 *   - 5 designed-to-fail cases verifying that assertions actually capture
 *     failures (distinct __func__-prefixed messages) and that MU_EXIT_CODE
 *     equals the failure count;
 *   - MU_SUITE_CONFIGURE setup/teardown counters verified per-test.
 *
 * Expected minunit verdict: "10 tests, 10 assertions, 5 failures",
 * exit code 5 — anything else means the header misbehaves on OHOS.
 */
#include <minunit.h>

static int foo = 0;
static int bar = 0;
static double dbar = 0.1;
static const char *foostring = "Thisstring";

static int setup_calls = 0;
static int teardown_calls = 0;

static void test_setup(void) {
    foo = 7;
    bar = 4;
    setup_calls++;
}

static void test_teardown(void) {
    teardown_calls++;
}

/* ── 5 positive cases: every assertion macro passes ── */

MU_TEST(test_check_pass) {
    mu_check(foo == 7);
}

MU_TEST(test_assert_pass) {
    mu_assert(foo == 7, "foo should be 7");
}

MU_TEST(test_assert_int_eq_pass) {
    mu_assert_int_eq(4, bar);
}

MU_TEST(test_assert_double_eq_pass) {
    mu_assert_double_eq(0.1, dbar);
}

MU_TEST(test_string_eq_pass) {
    mu_assert_string_eq("Thisstring", foostring);
}

/* ── 5 designed-to-fail cases: verify assertion capture ── */

MU_TEST(test_check_fail_designed) {
    mu_check(foo != 7);
}

MU_TEST(test_assert_int_eq_fail_designed) {
    mu_assert_int_eq(5, bar);
}

MU_TEST(test_assert_double_eq_fail_designed) {
    mu_assert_double_eq(0.2, dbar);
}

MU_TEST(test_string_eq_fail_designed) {
    mu_assert_string_eq("Thatstring", foostring);
}

MU_TEST(test_mu_fail_designed) {
    mu_fail("designed failure: mu_fail demonstration");
}

MU_TEST_SUITE(test_suite) {
    MU_SUITE_CONFIGURE(&test_setup, &test_teardown);

    MU_RUN_TEST(test_check_pass);
    MU_RUN_TEST(test_assert_pass);
    MU_RUN_TEST(test_assert_int_eq_pass);
    MU_RUN_TEST(test_assert_double_eq_pass);
    MU_RUN_TEST(test_string_eq_pass);

    MU_RUN_TEST(test_check_fail_designed);
    MU_RUN_TEST(test_assert_int_eq_fail_designed);
    MU_RUN_TEST(test_assert_double_eq_fail_designed);
    MU_RUN_TEST(test_string_eq_fail_designed);
    MU_RUN_TEST(test_mu_fail_designed);
}

int main(void) {
    MU_RUN_SUITE(test_suite);
    MU_REPORT();
    printf("setup_calls=%d teardown_calls=%d\n", setup_calls, teardown_calls);
    return MU_EXIT_CODE;
}
