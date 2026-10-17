/* test_package for jday/2.4 — exercises the libjday public API.
 *
 * Expected values are taken from the upstream RunTest suite, so this test
 * covers the same conversions the upstream project asserts on.
 */
#include <jday.h>
#include <stdio.h>

static int failures = 0;

static double diff(double a, double b)
{
    return (a > b) ? (a - b) : (b - a);
}

/* calendar date -> julian date */
static void expect_julian(int year, int month, int day,
                          int hour, int minute, double second,
                          double expected)
{
    UTinstant t;
    double jd;

    t.year = year;
    t.month = month;
    t.day = day;
    t.i_hour = hour;
    t.i_minute = minute;
    t.second = second;

    jd = JulDate(&t);
    if (diff(jd, expected) > 1.0e-5) {
        printf("FAIL JulDate(%d-%02d-%02d %02d:%02d) = %.6f, expected %.6f\n",
               year, month, day, hour, minute, jd, expected);
        failures++;
        return;
    }
    if (diff(t.j_date, expected) > 1.0e-5) {
        printf("FAIL JulDate did not store j_date (%.6f)\n", t.j_date);
        failures++;
        return;
    }
    printf("OK   JulDate(%d-%02d-%02d %02d:%02d) = %.6f\n",
           year, month, day, hour, minute, jd);
}

/* julian date -> calendar date */
static void expect_calendar(double jd, int year, int month, int day,
                            int hour, int minute)
{
    UTinstant t;

    t.j_date = jd;
    CalDate(&t);
    if (t.year != year || t.month != month || t.day != day ||
        t.i_hour != hour || t.i_minute != minute) {
        printf("FAIL CalDate(%.6f) = %d-%02d-%02d %02d:%02d, "
               "expected %d-%02d-%02d %02d:%02d\n",
               jd, t.year, t.month, t.day, t.i_hour, t.i_minute,
               year, month, day, hour, minute);
        failures++;
        return;
    }
    printf("OK   CalDate(%.6f) = %d-%02d-%02d %02d:%02d\n",
           jd, t.year, t.month, t.day, t.i_hour, t.i_minute);
}

int main(void)
{
    /* Unix epoch */
    expect_julian(1970, 1, 1, 0, 0, 0.0, 2440587.500000);
    /* Julian day zero */
    expect_julian(-4712, 1, 1, 12, 0, 0.0, 0.000000);
    /* Gregorian reform boundary */
    expect_julian(1582, 10, 15, 0, 0, 0.0, 2299160.500000);
    /* arbitrary instant with seconds */
    expect_julian(2000, 8, 18, 5, 25, 27.0, 2451774.726007);

    expect_calendar(2440587.500000, 1970, 1, 1, 0, 0);
    expect_calendar(0.000000, -4712, 1, 1, 12, 0);
    expect_calendar(2451774.726007, 2000, 8, 18, 5, 25);

    if (failures != 0) {
        printf("jday test_package: %d assertion(s) failed\n", failures);
        return 1;
    }
    printf("jday test_package: all 7 assertions passed\n");
    return 0;
}
