#include <math.h>
#include <stdio.h>
#include <stdlib.h>

#include <novas.h>

static void check(int condition, const char *message)
{
    if (!condition) {
        fprintf(stderr, "%s\n", message);
        exit(1);
    }
}

static void check_close(double actual, double expected, double tolerance, const char *message)
{
    check(fabs(actual - expected) <= tolerance, message);
}

int main(void)
{
    double jd = julian_date(2000, 1, 1, 12.0);
    short year = 0;
    short month = 0;
    short day = 0;
    double hour = 0.0;
    double vector[3] = {0.0, 0.0, 0.0};
    on_surface location;

    check_close(jd, NOVAS_JD_J2000, 1.0e-9, "julian_date J2000 mismatch");
    check(cal_date(jd, &year, &month, &day, &hour) == 0, "cal_date failed");
    check(year == 2000 && month == 1 && day == 1, "cal_date date mismatch");
    check_close(hour, 12.0, 1.0e-9, "cal_date hour mismatch");

    check(radec2vector(0.0, 0.0, 1.0, vector) == 0, "radec2vector failed");
    check_close(vector[0], 1.0, 1.0e-12, "radec2vector x mismatch");
    check_close(vector[1], 0.0, 1.0e-12, "radec2vector y mismatch");
    check_close(vector[2], 0.0, 1.0e-12, "radec2vector z mismatch");

    check(make_on_surface(30.0, 120.0, 50.0, 20.0, 1010.0, &location) == 0,
          "make_on_surface failed");
    check_close(location.latitude, 30.0, 1.0e-12, "latitude mismatch");
    check_close(location.longitude, 120.0, 1.0e-12, "longitude mismatch");
    check(SUPERNOVAS_MAJOR_VERSION == 1, "major version mismatch");

    return 0;
}
