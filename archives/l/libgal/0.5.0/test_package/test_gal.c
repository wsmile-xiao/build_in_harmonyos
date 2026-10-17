/*
 * test_gal.c - HarmonyOS consumer test for the static libgal package.
 *
 * Links libgal::libgal (static) and exercises public API entry points
 * from three different sub-libraries:
 *
 *   - date_time:  gal_cal2jd   (Gregorian calendar -> Julian Date)
 *   - vec_mat:    gal_pdp      (3-vector dot product)
 *   - sgp4:       gal_tlechksum (TLE modulo-10 checksum)
 *
 * Every assertion below is backed by either the documented API contract
 * (gal_cal2jd status codes, gal_tlechksum rule: first 68 characters,
 * letters/blanks/periods/plus signs = 0, minus signs = 1, digits summed,
 * result modulo 10) or by the checksum of the real ISS TLE line 2
 * (25544), whose trailing digit is the modulo-10 checksum of its first
 * 68 characters.
 *
 * Returns 0 when all assertions pass; the binary's exit code is the
 * canonical PASS/FAIL signal for the conan test_package phase.
 */

#include <stdio.h>
#include <string.h>

#include "gal.h"
#include "gal_tlechksum.h"

static int failures = 0;
static int assertions = 0;

static void check_eq_int(const char *label, int actual, int expected)
{
  assertions++;
  if (actual != expected) {
    failures++;
    printf("FAIL %s: expected %d, got %d\n", label, expected, actual);
  } else {
    printf("PASS %s (%d)\n", label, actual);
  }
}

static void check_eq_double(const char *label, double actual, double expected)
{
  assertions++;
  if (actual != expected) {
    failures++;
    printf("FAIL %s: expected %.10f, got %.10f\n", label, expected, actual);
  } else {
    printf("PASS %s (%.10f)\n", label, actual);
  }
}

static void check_eq_char(const char *label, char actual, char expected)
{
  assertions++;
  if (actual != expected) {
    failures++;
    printf("FAIL %s: expected '%c', got '%c'\n", label, expected, actual);
  } else {
    printf("PASS %s ('%c')\n", label, actual);
  }
}

int main(void)
{
  double djm0 = 0.0;
  double djm = 0.0;
  double a[3] = {1.0, 2.0, 3.0};
  double b[3] = {4.0, 5.0, 6.0};

  /*
   * gal_cal2jd: 2000-01-01 (0h) -> MJD 51544.0 with djm0 = 2400000.5,
   * i.e. Julian Date 2451544.5 (the J2000.0 epoch day).
   */
  check_eq_int("gal_cal2jd_status_20000101",
               gal_cal2jd(2000, 1, 1, &djm0, &djm), 0);
  check_eq_double("gal_cal2jd_djm0", djm0, 2400000.5);
  check_eq_double("gal_cal2jd_djm", djm, 51544.0);

  /* Documented status codes: bad month -> -2, bad day -> -3. */
  check_eq_int("gal_cal2jd_bad_month",
               gal_cal2jd(2000, 13, 1, &djm0, &djm), -2);
  check_eq_int("gal_cal2jd_bad_day",
               gal_cal2jd(2000, 1, 32, &djm0, &djm), -3);

  /* gal_pdp: (1,2,3).(4,5,6) = 32. */
  check_eq_double("gal_pdp_dot_product", gal_pdp(a, b), 32.0);

  /*
   * gal_tlechksum: real ISS (25544) TLE line 2; the trailing '7' is the
   * modulo-10 checksum of the first 68 characters.
   */
  {
    static char tle2[] =
        "2 25544  51.6416 247.4627 0006703 130.5360 325.0288 15.72125391563537";
    check_eq_int("tle2_length", (int)strlen(tle2), 69);
    check_eq_char("gal_tlechksum_iss_line2", gal_tlechksum(tle2), '7');
  }

  /*
   * gal_tlechksum: TLE-format line whose trailing checksum digit is
   * computed per the documented rule (digits summed modulo 10 over the
   * first 68 characters, '-' counts as 1).
   */
  {
    static char tle1[] =
        "1 25544U 98067A   08264.51782528 -.00002182  00000-0 -11606-4 0  9991";
    check_eq_char("gal_tlechksum_tle_format_line", gal_tlechksum(tle1), '1');
  }

  printf("GAL_CONSUMER_ASSERTIONS=%d/%d\n", assertions - failures, assertions);
  if (failures != 0) {
    printf("GAL_CONSUMER_TEST=FAIL\n");
    return 1;
  }
  printf("GAL_CONSUMER_TEST=PASS\n");
  return 0;
}
