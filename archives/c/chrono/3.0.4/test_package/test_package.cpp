#include <date/date.h>
#include <date/islamic.h>
#include <date/iso_week.h>
#include <date/julian.h>
#include <date/solar_hijri.h>
#include <date/tz.h>

#include <cstdlib>
#include <iostream>
#include <sstream>
#include <string>

namespace {

int checks = 0;

void expect(bool condition, const char* description)
{
    ++checks;
    if (!condition)
    {
        std::cerr << "check failed: " << description << '\n';
        std::exit(1);
    }
}

}  // namespace

int main()
{
    using namespace date;

    expect(year{2000}.is_leap(), "2000 is a leap year");
    expect(!year{1900}.is_leap(), "1900 is not a leap year");
    expect(year{2024}.is_leap(), "2024 is a leap year");
    expect(!year{2023}.is_leap(), "2023 is not a leap year");

    // Exercise Gregorian construction, validation, arithmetic, conversion and
    // weekday calculation across a broad range.  These are genuine API calls;
    // removing the package headers makes this test fail to compile.
    for (int value = 1990; value <= 2040; ++value)
    {
        const year_month_day original{year{value}, December, day{31}};
        expect(original.ok(), "Gregorian date is valid");
        const sys_days serial{original};
        const year_month_day roundtrip{serial};
        expect(roundtrip == original, "Gregorian sys_days roundtrip");
        expect(weekday{serial}.ok(), "weekday conversion is valid");
        expect((original + months{2}) - months{2} == original,
               "month arithmetic roundtrip");
    }

    const sys_days leap_day{year{2024} / February / day{29}};
    expect(format("%F", leap_day) == "2024-02-29", "ISO date formatting");

    std::istringstream input{"2025-07-22"};
    sys_days parsed;
    input >> parse("%F", parsed);
    expect(!input.fail(), "ISO date parsing succeeds");
    expect(year_month_day{parsed} == year{2025} / July / day{22},
           "parsed date has expected value");

    const iso_week::year_weeknum_weekday iso{sys_days{year{2020} / December / day{31}}};
    expect(iso.ok(), "ISO week date is valid");
    expect(iso == iso_week::year{2020} / iso_week::weeknum{53} / iso_week::thu,
           "2020-12-31 is ISO week 53 Thursday");

    const sys_days epoch{year{1970} / January / day{1}};
    const julian::year_month_day julian_date{epoch};
    expect(julian_date.ok(), "Julian date conversion is valid");
    expect(sys_days{julian_date} == epoch, "Julian calendar roundtrip");

    const islamic::year_month_day islamic_date{epoch};
    expect(islamic_date.ok(), "Islamic date conversion is valid");
    expect(sys_days{islamic_date} == epoch, "Islamic calendar roundtrip");

    const solar_hijri::year_month_day solar_date{epoch};
    expect(solar_date.ok(), "Solar Hijri date conversion is valid");
    expect(sys_days{solar_date} == epoch, "Solar Hijri calendar roundtrip");

    // This non-inline API is provided by libdate-tz.  Calling it proves the
    // consumer test links and executes the compiled timezone component while
    // avoiding any assumption about the device's zoneinfo directory.
    set_install("./tzdata/");
    expect(true, "date-tz manual install path API is callable");

    std::cout << "chrono checks passed: " << checks << '\n';
    return 0;
}
