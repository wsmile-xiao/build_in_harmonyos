/*
 * ryu 2.0 consumer test (test_package)
 *
 * Exercises the packaged library from a library-consumer perspective:
 *   1. d2s/f2s shortest-representation correctness (vectors reused from the
 *      upstream test suite: ryu/tests/d2s_test.cc D2sTest.Basic/SwitchToSubnormal/
 *      MinAndMax/Regression, ryu/tests/f2s_test.cc F2sTest.Basic/SwitchToSubnormal/
 *      MinAndMax/BoundaryRoundEven);
 *   2. d2s_buffered_n/f2s_buffered_n return length and buffered output;
 *   3. d2s()/f2s() heap-allocating APIs;
 *   4. shortest-representation round trip: strtod/strtof parsing the produced
 *      string must yield the bit-identical floating point value.
 *
 * Exit code 0 = all checks passed; 1 = at least one failure.
 */
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <ryu/ryu.h>

static int checks = 0;
static int failures = 0;

static void expect_str(const char* got, const char* want) {
  checks++;
  if (strcmp(got, want) != 0) {
    failures++;
    fprintf(stderr, "FAIL %d: got \"%s\", want \"%s\"\n", checks, got, want);
  }
}

static void expect_true(int cond) {
  checks++;
  if (!cond) {
    failures++;
    fprintf(stderr, "FAIL %d: condition is false\n", checks);
  }
}

int main(void) {
  char buf[64];
  int n;
  char* p;

  /* d2s buffered shortest output (upstream D2sTest.Basic) */
  d2s_buffered(0.0, buf);  expect_str(buf, "0E0");
  d2s_buffered(-0.0, buf); expect_str(buf, "-0E0");
  d2s_buffered(1.0, buf);  expect_str(buf, "1E0");
  d2s_buffered(-1.0, buf); expect_str(buf, "-1E0");
  d2s_buffered(NAN, buf);  expect_str(buf, "NaN");
  d2s_buffered(INFINITY, buf);  expect_str(buf, "Infinity");
  d2s_buffered(-INFINITY, buf); expect_str(buf, "-Infinity");

  /* d2s heap-allocating API */
  p = d2s(1.0);
  expect_str(p, "1E0");
  free(p);
  p = d2s(-2.109808898695963E16);
  expect_str(p, "-2.109808898695963E16");
  free(p);

  /* d2s_buffered_n: returned length matches written content (subnormal,
   * smallest denormal, largest finite double) */
  n = d2s_buffered_n(2.2250738585072014E-308, buf);
  buf[n] = '\0';
  expect_true(n == (int)strlen(buf));
  expect_str(buf, "2.2250738585072014E-308");

  n = d2s_buffered_n(5e-324, buf);
  buf[n] = '\0';
  expect_true(n == (int)strlen(buf));
  expect_str(buf, "5E-324");

  n = d2s_buffered_n(1.7976931348623157e308, buf);
  buf[n] = '\0';
  expect_true(n == (int)strlen(buf));
  expect_str(buf, "1.7976931348623157E308");

  /* f2s buffered shortest output (upstream F2sTest.Basic/SwitchToSubnormal) */
  f2s_buffered(0.0f, buf);  expect_str(buf, "0E0");
  f2s_buffered(-0.0f, buf); expect_str(buf, "-0E0");
  f2s_buffered(1.1754944E-38f, buf); expect_str(buf, "1.1754944E-38");

  /* f2s_buffered_n: returned length matches written content */
  n = f2s_buffered_n(3.4028235E38f, buf);
  buf[n] = '\0';
  expect_true(n == (int)strlen(buf));
  expect_str(buf, "3.4028235E38");

  n = f2s_buffered_n(1e-45f, buf);
  buf[n] = '\0';
  expect_true(n == (int)strlen(buf));
  expect_str(buf, "1E-45");

  /* f2s heap-allocating API (upstream F2sTest.BoundaryRoundEven vector) */
  p = f2s(3.355445E7f);
  expect_str(p, "3.355445E7");
  free(p);

  /* shortest-representation round trip: parse back, compare bit patterns */
  {
    double dv = 3.141592653589793;
    double dback;
    d2s_buffered(dv, buf);
    dback = strtod(buf, NULL);
    expect_true(memcmp(&dv, &dback, sizeof(double)) == 0);
  }
  {
    float fv = 2.718281828459045f;
    float fback;
    f2s_buffered(fv, buf);
    fback = strtof(buf, NULL);
    expect_true(memcmp(&fv, &fback, sizeof(float)) == 0);
  }

  if (failures != 0) {
    fprintf(stderr, "test ryu 2.0: FAILED (%d/%d checks failed)\n", failures, checks);
    return 1;
  }
  printf("test ryu 2.0: OK (%d checks passed)\n", checks);
  return 0;
}
