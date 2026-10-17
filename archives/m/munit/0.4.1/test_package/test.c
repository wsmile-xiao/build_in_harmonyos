/* Test munit library by implementing a simple test suite */
#include "munit.h"
#include <stdio.h>
#include <string.h>

/* Basic test - check that assertions work */
static MunitResult
test_basic(const MunitParameter params[], void* data) {
    (void) params;
    (void) data;
    
    munit_assert_int(1 + 1, ==, 2);
    munit_assert_true(1 == 1);
    munit_assert_false(0 == 1);
    
    return MUNIT_OK;
}

/* String test - check string assertions */
static MunitResult
test_strings(const MunitParameter params[], void* data) {
    (void) params;
    (void) data;
    
    const char* str = "hello";
    munit_assert_string_equal(str, "hello");
    munit_assert_size(strlen(str), ==, 5);
    
    return MUNIT_OK;
}

/* Random number test */
static MunitResult
test_rand(const MunitParameter params[], void* data) {
    (void) params;
    (void) data;
    
    int val = munit_rand_int_range(0, 100);
    munit_assert_int(val, >=, 0);
    munit_assert_int(val, <=, 100);
    
    return MUNIT_OK;
}

/* Define the test suite */
static MunitTest test_suite_tests[] = {
    { (char*) "/basic", test_basic, NULL, NULL, MUNIT_TEST_OPTION_NONE, NULL },
    { (char*) "/strings", test_strings, NULL, NULL, MUNIT_TEST_OPTION_NONE, NULL },
    { (char*) "/rand", test_rand, NULL, NULL, MUNIT_TEST_OPTION_NONE, NULL },
    { NULL, NULL, NULL, NULL, MUNIT_TEST_OPTION_NONE, NULL }
};

static const MunitSuite test_suite = {
    (char*) "",
    test_suite_tests,
    NULL,
    1,
    MUNIT_SUITE_OPTION_NONE
};

int main(int argc, char* argv[MUNIT_ARRAY_PARAM(argc + 1)]) {
    return munit_suite_main(&test_suite, NULL, argc, argv);
}
