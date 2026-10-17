/*
 * test_package consumer for bcunit 5.3.113.
 *
 * Exercises the public BCUnit API against the packaged library:
 *   - registry / suite / test registration and the basic runner counters
 *   - CU_Suite.pUserData round-trip (5.3.x line API)
 *   - the automated JUnit writer, both with the default englobing
 *     <testsuites> tag and with CU_automated_enable_partial_junit() (5.3.x
 *     line API) that drops it
 *   - CU_set_trace_handler() being reachable from the framework's own output
 *     path (the code path touched by the CU_trace_handler storage fix)
 *
 * The upstream automated interface may only run once per process (a second
 * CU_automated_run_tests() call in the same process crashes upstream 5.3.113,
 * reproducible with the unpatched library), so the JUnit modes are checked in
 * two separate invocations of this binary:
 *
 *   test_bcunit            -> basic runner, JUnit full report, trace handler
 *   test_bcunit partial    -> JUnit partial report
 *
 * Every check is counted; each invocation exits non-zero if any check fails.
 * Generated JUnit files are written to the current working directory, which
 * the test_package conanfile sets to the Conan build folder.
 */

#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "BCUnit/BCUnit.h"
#include "BCUnit/Automated.h"
#include "BCUnit/Basic.h"
#include "BCUnit/Util.h"

static const char *g_suite_user_data = "suite-user-data-sentinel";

static int g_checks = 0;
static int g_failed_checks = 0;
static int g_trace_calls = 0;
static int g_trace_error_level_calls = 0;

static void check(int condition, const char *what)
{
  g_checks++;
  if (!condition) {
    g_failed_checks++;
    fprintf(stderr, "CHECK FAILED: %s\n", what);
  }
}

static int file_contains(const char *path, const char *needle)
{
  static char buffer[65536];
  size_t used;
  FILE *file = fopen(path, "rb");

  if (NULL == file) {
    return 0;
  }
  used = fread(buffer, 1, sizeof(buffer) - 1, file);
  fclose(file);
  buffer[used] = '\0';
  return (NULL != strstr(buffer, needle));
}

static void trace_probe(int level, const char *fmt, va_list args)
{
  char buffer[512];

  g_trace_calls++;
  if (0 != level) {
    g_trace_error_level_calls++;
  }
  /* Format only: never re-enter fprintf, which would recurse. */
  vsnprintf(buffer, sizeof(buffer), fmt, args);
}

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

static void test_suite_user_data(void)
{
  CU_pSuite suite = CU_get_current_suite();

  CU_ASSERT_PTR_NOT_NULL_FATAL(suite);
  CU_ASSERT_PTR_EQUAL(suite->pUserData, (const void *)g_suite_user_data);
}

static CU_pSuite add_smoke_suite(void)
{
  CU_pSuite suite = CU_add_suite("bcunit_smoke", suite_init, suite_clean);

  if (NULL == suite) {
    fprintf(stderr, "CU_add_suite failed: %s\n", CU_get_error_msg());
    return NULL;
  }
  /* 5.3.x API: the consumer attaches its own context to the suite. */
  suite->pUserData = (void *)g_suite_user_data;
  return suite;
}

static int report(const char *mode, unsigned int runs, unsigned int failures,
                  unsigned int asserts)
{
  printf("bcunit smoke [%s]: tests_run=%u failures=%u asserts=%u "
         "checks=%d failed_checks=%d trace_calls=%d\n",
         mode, runs, failures, asserts, g_checks, g_failed_checks,
         g_trace_calls);
  return (0 == g_failed_checks) ? 0 : 1;
}

/* Default mode: basic runner, counters, suite user data, full JUnit report,
 * trace handler.  One automated run only. */
static int run_full_mode(void)
{
  unsigned int failures;
  unsigned int runs;
  unsigned int asserts;
  CU_pSuite suite;
  int result;

  if (CUE_SUCCESS != CU_initialize_registry()) {
    fprintf(stderr, "CU_initialize_registry failed: %s\n", CU_get_error_msg());
    return 1;
  }

  suite = add_smoke_suite();
  if ((NULL == suite) ||
      (NULL == CU_add_test(suite, "arithmetic", test_arithmetic)) ||
      (NULL == CU_add_test(suite, "strings", test_strings)) ||
      (NULL == CU_add_test(suite, "suite_user_data", test_suite_user_data))) {
    fprintf(stderr, "test registration failed: %s\n", CU_get_error_msg());
    CU_cleanup_registry();
    return 1;
  }

  CU_basic_set_mode(CU_BRM_VERBOSE);
  CU_basic_run_tests();

  runs = CU_get_number_of_tests_run();
  failures = CU_get_number_of_failures();
  asserts = CU_get_number_of_asserts();

  check(3 == runs, "CU_get_number_of_tests_run() == 3");
  check(0 == failures, "CU_get_number_of_failures() == 0");
  check(asserts >= 6, "CU_get_number_of_asserts() >= 6");

  /* Automated JUnit interface, default (non-partial) report: the package's
   * own default is CU_automated_enable_partial_junit(CU_FALSE). */
  CU_automated_enable_junit_xml(CU_TRUE);
  CU_automated_enable_partial_junit(CU_FALSE);
  CU_set_output_filename("bcunit-junit-full");
  CU_automated_run_tests();

  check(file_contains("bcunit-junit-full-Results.xml", "<testsuites>"),
        "full JUnit report contains the englobing <testsuites> tag");
  check(file_contains("bcunit-junit-full-Results.xml", "<testsuite "),
        "full JUnit report contains a <testsuite> entry");

  /* Trace handler: install a probe; the framework's own output path must
   * route through it (this is the storage the packaging patch relocated). */
  CU_set_trace_handler(trace_probe);
  CU_basic_run_tests();
  CU_set_trace_handler(NULL);

  check(g_trace_calls > 0, "CU_set_trace_handler() probe received calls");

  result = report("full", runs, failures, asserts);
  CU_cleanup_registry();
  return result;
}

/* Partial mode: single automated run with the englobing tag disabled. */
static int run_partial_mode(void)
{
  unsigned int failures;
  unsigned int runs;
  CU_pSuite suite;
  int result;

  if (CUE_SUCCESS != CU_initialize_registry()) {
    fprintf(stderr, "CU_initialize_registry failed: %s\n", CU_get_error_msg());
    return 1;
  }

  suite = add_smoke_suite();
  if ((NULL == suite) ||
      (NULL == CU_add_test(suite, "arithmetic", test_arithmetic)) ||
      (NULL == CU_add_test(suite, "suite_user_data", test_suite_user_data))) {
    fprintf(stderr, "test registration failed: %s\n", CU_get_error_msg());
    CU_cleanup_registry();
    return 1;
  }

  CU_automated_enable_junit_xml(CU_TRUE);
  CU_automated_enable_partial_junit(CU_TRUE);
  CU_set_output_filename("bcunit-junit-partial");
  CU_automated_run_tests();

  runs = CU_get_number_of_tests_run();
  failures = CU_get_number_of_failures();

  check(2 == runs, "CU_get_number_of_tests_run() == 2");
  check(0 == failures, "CU_get_number_of_failures() == 0");
  check(!file_contains("bcunit-junit-partial-Results.xml", "<testsuites"),
        "partial JUnit report has no englobing <testsuites> tag");
  check(file_contains("bcunit-junit-partial-Results.xml", "<testsuite "),
        "partial JUnit report still contains a <testsuite> entry");

  result = report("partial", runs, failures, CU_get_number_of_asserts());
  CU_cleanup_registry();
  return result;
}

int main(int argc, char **argv)
{
  if ((argc > 1) && (0 == strcmp(argv[1], "partial"))) {
    return run_partial_mode();
  }
  return run_full_mode();
}
