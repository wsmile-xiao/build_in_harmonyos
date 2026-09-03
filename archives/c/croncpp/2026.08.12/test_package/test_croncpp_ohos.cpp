// croncpp OHOS consumer test — L1 test_package (runs on HarmonyOS aarch64 host).
//
// HarmonyOS-specific focus: exercises the header-only library end-to-end on the
// OHOS libc/clang toolchain (std::mktime/localtime_r via cron::utils, tzset
// under TZ=UTC for deterministic expectations), covering parsing, next/prev
// occurrence, traits dialects, invalid-expression rejection, year-field
// exhaustion and the chrono overload.
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <ctime>
#include <chrono>
#include <string>

#include "croncpp.h"

static int g_checks = 0;
static int g_failures = 0;

#define CHECK(cond, msg)                                            \
    do {                                                            \
        ++g_checks;                                                 \
        if (cond) {                                                 \
            std::printf("[PASS] %s\n", msg);                        \
        } else {                                                    \
            ++g_failures;                                           \
            std::printf("[FAIL] %s (line %d)\n", msg, __LINE__);    \
        }                                                           \
    } while (0)

namespace
{
    // Build a broken-down time (local time; the process pins TZ=UTC).
    std::tm make_tm(int y, int mo, int d, int h, int mi, int s)
    {
        std::tm t{};
        t.tm_year = y - 1900;
        t.tm_mon = mo - 1;
        t.tm_mday = d;
        t.tm_hour = h;
        t.tm_min = mi;
        t.tm_sec = s;
        t.tm_isdst = -1;
        return t;
    }

    bool same_fields(std::tm const& a, std::tm const& b)
    {
        return a.tm_sec == b.tm_sec && a.tm_min == b.tm_min &&
               a.tm_hour == b.tm_hour && a.tm_mday == b.tm_mday &&
               a.tm_mon == b.tm_mon && a.tm_year == b.tm_year;
    }
} // namespace

int main()
{
    using namespace cron;

    // Deterministic expectations: pin to UTC on OHOS libc.
    setenv("TZ", "UTC", 1);
    tzset();

    // 1) Parse a plain standard expression.
    auto daily = make_cron("0 30 8 * * *");
    CHECK(!daily.empty(), "make_cron parses '0 30 8 * * *'");
    CHECK(daily == make_cron("0 30 8 * * *"), "parsed expression is stable (operator==)");

    // 2) Next occurrence from 2026-09-03 00:00:00 UTC -> 2026-09-03 08:30:00 UTC.
    auto from = make_tm(2026, 9, 3, 0, 0, 0);
    auto next = cron_next(daily, from);
    auto exp = make_tm(2026, 9, 3, 8, 30, 0);
    CHECK(same_fields(next, exp), "cron_next(tm) -> 2026-09-03 08:30:00 UTC");

    // 3) time_t overload agrees with the tm overload.
    std::time_t const from_t = std::mktime(&from);
    std::time_t const next_t = cron_next(daily, from_t);
    std::time_t const exp_t = std::mktime(&exp);
    CHECK(next_t == exp_t, "cron_next(time_t) equals mktime(expected)");
    CHECK(next_t != INVALID_TIME, "next occurrence found (not INVALID_TIME)");

    // 4) quartz traits: day-of-month restricted, DOW '?' -> valid; next = Sep 15.
    auto quartz = make_cron<cron_quartz_traits>("0 0 12 15 * ?");
    auto q_from = make_tm(2026, 9, 1, 0, 0, 0);
    auto q_next = cron_next<cron_quartz_traits>(quartz, q_from);
    auto q_exp = make_tm(2026, 9, 15, 12, 0, 0);
    CHECK(same_fields(q_next, q_exp), "quartz traits: 15th of month at noon");

    // 5) quartz rejects expressions that restrict BOTH day fields.
    bool rejected = false;
    try {
        make_cron<cron_quartz_traits>("0 0 12 15 * 1");
    } catch (bad_cronexpr const& e) {
        rejected = true;
        std::printf("       quartz rejection message: %s\n", e.what());
    }
    CHECK(rejected, "quartz rejects restricted DOM+DOW (dialect rule)");

    // 6) Unreachable date (Feb 31) is rejected at parse time.
    bool bad_date = false;
    try {
        make_cron("0 0 12 31 2 *");
    } catch (bad_cronexpr const&) {
        bad_date = true;
    }
    CHECK(bad_date, "make_cron rejects '31st of February'");

    // 7) Empty expression is rejected.
    bool bad_empty = false;
    try {
        make_cron("");
    } catch (bad_cronexpr const&) {
        bad_empty = true;
    }
    CHECK(bad_empty, "make_cron rejects empty expression");

    // 8) Year field in the past has no next occurrence -> INVALID_TIME.
    //    Seven-field form: sec min hour dom month dow year.
    auto past_year = make_cron("0 0 0 * * * 2020");
    std::time_t const past_next = cron_next(past_year, from_t);
    CHECK(past_next == INVALID_TIME, "exhausted year field -> INVALID_TIME");

    // 9) cron_prev finds the last occurrence strictly before the given time.
    //    8:30 daily, asked at 2026-09-05 12:00 -> 2026-09-05 08:30.
    auto prev_from = make_tm(2026, 9, 5, 12, 0, 0);
    std::time_t const prev_t = cron_prev(daily, std::mktime(&prev_from));
    auto prev_exp = make_tm(2026, 9, 5, 8, 30, 0);
    CHECK(prev_t == std::mktime(&prev_exp), "cron_prev -> 2026-09-05 08:30:00 UTC");

    // 10) chrono overload keeps duration and matches the time_t result.
    auto tp = std::chrono::system_clock::from_time_t(from_t);
    auto tp_next = cron_next(daily, tp);
    CHECK(tp_next.time_since_epoch() ==
          std::chrono::seconds(next_t - from_t) + tp.time_since_epoch(),
          "chrono overload consistent with time_t overload");

    // 11) utils round-trip on OHOS libc (mktime + localtime_r).
    std::tm rt;
    std::time_t const rt_src = exp_t;
    cron::utils::time_to_tm(&rt_src, &rt);
    CHECK(same_fields(rt, exp), "utils::time_to_tm round-trip on OHOS libc");

    std::printf("== croncpp OHOS test: %d checks, %d failures ==\n",
                g_checks, g_failures);
    return g_failures == 0 ? 0 : 1;
}
