#include <cmath>
#include <cstdlib>
#include <iostream>

#include <supernovas.h>

static void check(bool condition, const char *message)
{
    if (!condition) {
        std::cerr << message << std::endl;
        std::exit(1);
    }
}

static void check_close(double actual, double expected, double tolerance, const char *message)
{
    check(std::fabs(actual - expected) <= tolerance, message);
}

int main()
{
    using namespace supernovas;

    Time invalid = Time::undefined();
    check(!invalid.is_valid(), "undefined time should be invalid");

    EOP eop(32, 0.1, 0.2 * Unit::arcsec, 0.3 * Unit::arcsec);
    Time j2000(NOVAS_JD_J2000, eop, NOVAS_UTC);
    check(j2000.is_valid(), "J2000 time should be valid");
    check_close(j2000.jd(NOVAS_UTC), NOVAS_JD_J2000, 1.0e-8, "J2000 jd mismatch");
    check_close(j2000.time_of_day(NOVAS_UTC).hours(), 12.0, 1.0e-7, "time of day mismatch");

    Angle angle(45.0 * Unit::deg);
    check(angle.is_valid(), "angle should be valid");
    check_close(angle.deg(), 45.0, 1.0e-12, "angle deg mismatch");

    CalendarDate date = j2000.to_calendar_date(NOVAS_UTC);
    check(date.is_valid(), "calendar date should be valid");
    check_close(date.jd(), NOVAS_JD_J2000, 1.0e-8, "calendar date jd mismatch");

    return 0;
}
