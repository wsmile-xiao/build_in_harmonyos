// test_package/test_boost1_84_date_time.cpp — boost1.84-date_time 1.84.0
// consumer test (L1, upstream-derived).
//
// Derived from the upstream Boost.Date_Time test suite (libs/date_time/test/,
// Boost Software License 1.0). Exercises:
//   - gregorian calendar: date construction, calendar arithmetic, month lengths
//     (upstream testgreg_cal.cpp / testgreg_month.cpp coverage)
//   - date duration and iterators (upstream testdate.cpp / testdate_duration.cpp)
//   - posix_time::ptime construction, arithmetic and time_duration
//     (upstream testtime.cpp / testduration.cpp)
// The upstream testfrmwk.hpp-style check counting is preserved so the pass
// count is reported like the upstream suite.
#include <iostream>
#include <string>
#include <sstream>

#include <boost/date_time/gregorian/gregorian.hpp>
#include <boost/date_time/posix_time/posix_time.hpp>

namespace greg = boost::gregorian;
namespace pt = boost::posix_time;

static int g_checks = 0;
static int g_failures = 0;

#define CHECK(cond) do { \
    ++g_checks; \
    if (!(cond)) { \
        ++g_failures; \
        std::cerr << "FAIL line " << __LINE__ << ": " #cond << std::endl; \
    } \
} while (0)

int main() {
    // ── gregorian calendar: construction ─────────────────────────────────
    greg::date d(2026, 9, 5);
    CHECK(d.year() == 2026);
    CHECK(d.month() == 9);
    CHECK(d.day() == 5);
    CHECK(!d.is_not_a_date());
    CHECK(!d.is_neg_infinity());
    CHECK(!d.is_pos_infinity());

    // day-of-week / day-of-year come from the calendar math
    CHECK(d.day_of_week() == greg::Saturday);
    CHECK(d.day_of_year() == 248);
    CHECK(d.week_number() == 36);

    // ── gregorian calendar: leap-year month lengths (testgreg_cal) ────────
    CHECK(greg::gregorian_calendar::end_of_month_day(2024, 2) == 29);
    CHECK(greg::gregorian_calendar::end_of_month_day(2025, 2) == 28);
    CHECK(greg::gregorian_calendar::end_of_month_day(2026, 1) == 31);
    CHECK(greg::gregorian_calendar::end_of_month_day(2026, 4) == 30);
    CHECK(greg::gregorian_calendar::is_leap_year(2024));
    CHECK(!greg::gregorian_calendar::is_leap_year(2025));
    CHECK(!greg::gregorian_calendar::is_leap_year(1900));  // century rule
    CHECK(greg::gregorian_calendar::is_leap_year(2000));   // 400-year rule

    // ── date arithmetic and durations (testdate / testdate_duration) ─────
    greg::date_duration dd(10);
    greg::date later = d + dd;
    CHECK(later == greg::date(2026, 9, 15));
    greg::date earlier = d - greg::date_duration(5);
    CHECK(earlier == greg::date(2026, 8, 31));
    CHECK(d - later == greg::date_duration(-10));

    // month/year traversal across boundaries
    greg::first_day_of_the_week_in_month fdm(greg::Monday, greg::Sep);
    greg::date first_monday = fdm.get_date(2026);
    CHECK(first_monday == greg::date(2026, 9, 7));
    greg::last_day_of_the_week_in_month ldm(greg::Friday, greg::Sep);
    CHECK(ldm.get_date(2026) == greg::date(2026, 9, 25));

    // date iterator (prefix increment/decrement are provided)
    greg::day_iterator dit(d);
    ++dit;
    CHECK(*dit == greg::date(2026, 9, 6));
    --dit;
    CHECK(*dit == greg::date(2026, 9, 5));

    // to_string round-trip (formatters)
    std::string iso = boost::gregorian::to_iso_extended_string(d);
    CHECK(iso == "2026-09-05");
    std::string d_iso = boost::gregorian::to_iso_string(d);
    CHECK(d_iso == "20260905");
    // from_string / from_simple_string parsers (locale-independent paths)
    CHECK(greg::from_string("2026-01-01") == greg::date(2026, 1, 1));
    CHECK(greg::from_undelimited_string("20260101") == greg::date(2026, 1, 1));
    CHECK(greg::from_simple_string("2026-Jan-01") == greg::date(2026, 1, 1));

    // ── posix_time::ptime construction and arithmetic (testtime) ─────────
    pt::ptime t0(greg::date(2026, 9, 5), pt::hours(12) + pt::minutes(34) + pt::seconds(56));
    CHECK(t0.date() == greg::date(2026, 9, 5));
    CHECK(t0.time_of_day().hours() == 12);
    CHECK(t0.time_of_day().minutes() == 34);
    CHECK(t0.time_of_day().seconds() == 56);

    pt::time_duration td = pt::hours(1) + pt::minutes(30);
    pt::ptime t1 = t0 + td;
    CHECK(t1 == pt::ptime(greg::date(2026, 9, 5), pt::hours(14) + pt::minutes(4) + pt::seconds(56)));
    CHECK(t1 > t0);
    CHECK(t1 - t0 == td);

    // ptime across a day boundary
    pt::ptime t2 = t0 + pt::hours(12);
    CHECK(t2.date() == greg::date(2026, 9, 6));
    CHECK(t2.time_of_day().hours() == 0);

    // microseconds precision of time_duration
    pt::time_duration us = pt::microseconds(1500);
    CHECK(us.total_microseconds() == 1500);
    CHECK(us.total_milliseconds() == 1);

    // ptime -> string formatters (to_iso_extended_string uses 'T' separator,
    // matching upstream testtime_formatters.cpp expectations)
    CHECK(pt::to_iso_string(t0) == std::string("20260905T123456"));
    CHECK(pt::to_simple_string(t0) == std::string("2026-Sep-05 12:34:56"));

    // special values
    pt::ptime nat(pt::not_a_date_time);
    CHECK(nat.is_not_a_date_time());
    CHECK(!t0.is_not_a_date_time());

    // period logic
    greg::date_period dp(greg::date(2026, 9, 1), greg::date(2026, 9, 30));
    CHECK(dp.contains(d));
    CHECK(!dp.contains(greg::date(2026, 10, 1)));

    std::cout << g_checks << " checks: " << g_failures << " failures" << std::endl;
    return g_failures == 0 ? 0 : 1;
}
