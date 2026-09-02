#include <stdint.h>
#include <string.h>

#include "munit.h"

static MunitResult
test_assertions(const MunitParameter params[], void* data) {
  const char payload[] = "munit";
  (void) params;
  (void) data;

  munit_assert_int(2 + 3, ==, 5);
  munit_assert_string_equal(payload, "munit");
  munit_assert_memory_equal(sizeof(payload), payload, "munit");
  munit_assert_not_null(payload);
  return MUNIT_OK;
}

static MunitResult
test_random_api(const MunitParameter params[], void* data) {
  int value;
  double unit;
  (void) params;
  (void) data;

  value = munit_rand_int_range(7, 9);
  unit = munit_rand_double();
  munit_assert_int(value, >=, 7);
  munit_assert_int(value, <=, 9);
  munit_assert_double(unit, >=, 0.0);
  munit_assert_double(unit, <=, 1.0);
  return MUNIT_OK;
}

static MunitTest tests[] = {
  { (char*) "/consumer/assertions", test_assertions, NULL, NULL, MUNIT_TEST_OPTION_NONE, NULL },
  { (char*) "/consumer/random-api", test_random_api, NULL, NULL, MUNIT_TEST_OPTION_NONE, NULL },
  { NULL, NULL, NULL, NULL, MUNIT_TEST_OPTION_NONE, NULL }
};

static const MunitSuite suite = {
  "",
  tests,
  NULL,
  1,
  MUNIT_SUITE_OPTION_NONE
};

int
main(int argc, char* argv[MUNIT_ARRAY_PARAM(argc + 1)]) {
  return munit_suite_main(&suite, NULL, argc, argv);
}
