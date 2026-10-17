// test.cpp — consumer test for cpp-datetime-library 1.0.2 (HarmonyOS)
//
// Uses only the installed public API (jed_utils::datetime / jed_utils::timespan)
// to verify a third-party consumer can compile, link and run against the
// package. Exercises a meaningful public API call with observable results.

#include <cassert>
#include <iostream>
#include <string>

#include "datetime/datetime.h"
#include "datetime/timespan.h"

int main() {
    using jed_utils::datetime;
    using jed_utils::timespan;
    using jed_utils::period;

    // 1) Construct a datetime with a known value and verify round-trip output.
    datetime dt(2016, 11, 25, 20, 12, 44);
    assert(dt.get_year() == 2016);
    assert(dt.get_month() == 11);
    assert(dt.get_day() == 25);
    assert(dt.get_hour() == 20);
    assert(dt.get_minute() == 12);
    assert(dt.get_second() == 44);

    // 2) String formatting is a public, observable behavior.
    std::string iso = dt.to_string("yyyy-MM-dd HH:mm:ss");
    assert(iso == "2016-11-25 20:12:44");

    // 3) add_days() is a mutating public API.
    dt.add_days(7);
    assert(dt.get_day() == 2);
    assert(dt.get_month() == 12);
    assert(dt.get_year() == 2016);

    // 4) Leap-year logic.
    assert(datetime::is_leapyear(2020) == true);
    assert(datetime::is_leapyear(2019) == false);

    // 5) timespan public API: construction and total-seconds arithmetic.
    timespan ts(1, 2, 3, 4);
    assert(ts.get_total_seconds() == (1 * 86400 + 2 * 3600 + 3 * 60 + 4));

    // 6) datetime subtraction yields a timespan (observable difference).
    datetime d1(2016, 11, 25);
    datetime d2(2016, 11, 20);
    timespan diff = d1 - d2;
    assert(diff.get_days() == 5);

    std::cout << "consumer test OK: datetime=" << dt.to_string("yyyy-MM-dd")
              << " diff_days=" << diff.get_days() << std::endl;
    return 0;
}
