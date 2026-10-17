/*
 * test_package consumer for bcunit: exercises the public BCUnit API
 * (registry, suite, tests, assert implementation, basic runner, result
 * counters) and verifies real behaviour.
 */

#include <stdio.h>

#include "BCUnit/BCUnit.h"
#include "BCUnit/Basic.h"

static int suite_init(void)
{
  return 0;
}

static int suite_clean(void)
{
  return 0;
}

static void test_arithmetic(void)
{
  CU_ASSERT(2 + 2 == 4);
  CU_ASSERT_FATAL(1 < 2);
}

static void test_strings(void)
{
  CU_ASSERT_STRING_EQUAL("bcunit", "bcunit");
  CU_ASSERT_PTR_NOT_NULL("non-null");
}

int main(void)
{
  unsigned int failures;
  unsigned int runs;
  CU_pSuite suite;

  if (CUE_SUCCESS != CU_initialize_registry()) {
    fprintf(stderr, "CU_initialize_registry failed: %s\n",
            CU_get_error_msg());
    return 1;
  }

  suite = CU_add_suite("bcunit_smoke", suite_init, suite_clean);
  if (NULL == suite) {
    CU_cleanup_registry();
    return 1;
  }

  if ((NULL == CU_add_test(suite, "arithmetic", test_arithmetic)) ||
      (NULL == CU_add_test(suite, "strings", test_strings))) {
    CU_cleanup_registry();
    return 1;
  }

  CU_basic_set_mode(CU_BRM_VERBOSE);
  CU_basic_run_tests();

  failures = CU_get_number_of_failures();
  runs = CU_get_number_of_tests_run();
  printf("bcunit smoke: tests_run=%u failures=%u\n", runs, failures);

  CU_cleanup_registry();

  if ((2 != runs) || (0 != failures)) {
    return 1;
  }
  return 0;
}
