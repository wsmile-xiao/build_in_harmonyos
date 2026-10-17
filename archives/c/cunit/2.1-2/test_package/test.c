/* Consumer tests for the CUnit 2.1-2 package. */
#include <stdio.h>
#include <CUnit/CUnit.h>
#include <CUnit/Basic.h>

static void test_addition(void) {
    CU_ASSERT_EQUAL(1 + 1, 2);
}

static void test_multiplication(void) {
    CU_ASSERT_EQUAL(2 * 3, 6);
}

static void test_string_equality(void) {
    CU_ASSERT_STRING_EQUAL("cunit", "cunit");
}

int main(void) {
    CU_pSuite suite;
    int result;

    if (CU_initialize_registry() != CUE_SUCCESS) {
        fprintf(stderr, "CU_initialize_registry failed: %d\n", CU_get_error());
        return 1;
    }

    suite = CU_add_suite("cunit_consumer", NULL, NULL);
    if (suite == NULL ||
        CU_add_test(suite, "addition", test_addition) == NULL ||
        CU_add_test(suite, "multiplication", test_multiplication) == NULL ||
        CU_add_test(suite, "string equality", test_string_equality) == NULL) {
        fprintf(stderr, "CUnit test registration failed: %d\n", CU_get_error());
        CU_cleanup_registry();
        return 1;
    }

    CU_basic_set_mode(CU_BRM_VERBOSE);
    result = CU_basic_run_tests();
    if (result != CUE_SUCCESS || CU_get_number_of_tests_failed() != 0) {
        fprintf(stderr, "CUnit consumer tests failed: %d\n", result);
        CU_cleanup_registry();
        return 1;
    }

    CU_cleanup_registry();
    puts("PASS: 3 CUnit consumer test cases");
    return 0;
}
