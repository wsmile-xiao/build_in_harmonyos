// test_package for scnlib/4.0.1 — consumer test on OpenHarmony PC (aarch64)
//
// Exercises the main scanning APIs end-to-end through the installed library:
//   1. scn::scan for int (core path)
//   2. Floating-point scanning (fast_float backend via external dependency)
//   3. Multiple-value and string scanning
//   4. Error handling (type mismatch -> scan_error)
//   5. Wide-char scanning (scn/xchar.h)
//   6. Range scanning (scn/ranges.h: std::vector sequence)
//   7. scan_int fast path
//
// Any failure aborts with a non-zero exit code.

#include <scn/scan.h>
#include <scn/xchar.h>
#include <scn/ranges.h>

#include <cmath>
#include <cstdio>
#include <string>
#include <string_view>
#include <vector>

static int failures = 0;

#define CHECK(cond, msg)                             \
    do {                                             \
        if (!(cond)) {                               \
            std::fprintf(stderr, "FAIL: %s\n", msg); \
            ++failures;                              \
        }                                            \
    } while (false)

int main()
{
    // 1. Basic integer scanning
    {
        auto result = scn::scan<int>("123", "{}");
        CHECK(result, "scan<int> from \"123\" should succeed");
        if (result) {
            CHECK(result->value() == 123, "scn::scan<int> should yield 123");
        }
    }

    // 2. Multiple values, mixed types (int + double)
    {
        auto result = scn::scan<int, double>("7 3.25", "{} {}");
        CHECK(result, "scan<int,double> should succeed");
        if (result) {
            CHECK(std::get<0>(result->values()) == 7, "scanned int should be 7");
            CHECK(std::get<1>(result->values()) == 3.25,
                  "scanned double should be 3.25");
        }
    }

    // 3. Floating point via fast_float backend (external dependency path)
    {
        auto result = scn::scan<double>("3.14159", "{}");
        CHECK(result, "scan<double> should succeed");
        if (result) {
            CHECK(std::fabs(result->value() - 3.14159) < 1e-6,
                  "scanned double should be ~3.14159");
        }
    }

    // 4. String scanning
    {
        auto result = scn::scan<std::string>("hello", "{}");
        CHECK(result, "scan<string> should succeed");
        if (result) {
            CHECK(result->value() == "hello", "scanned string should be \"hello\"");
        }
    }

    // 5. Whitespace skipping and negative numbers
    {
        auto result = scn::scan<int>("   -17", "{}");
        CHECK(result, "scan<int> with leading whitespace should succeed");
        if (result) {
            CHECK(result->value() == -17, "scanned int should be -17");
        }
    }

    // 6. Error handling: type mismatch must produce an error, not UB
    {
        auto result = scn::scan<int>("notanumber", "{}");
        CHECK(!result, "scan<int> from \"notanumber\" must fail");
        if (!result) {
            CHECK(result.error().code() == scn::scan_error::invalid_scanned_value,
                  "error code should be invalid_scanned_value");
        }
    }

    // 7. Wide-char scanning (xchar)
    {
        auto result = scn::scan<int>(L"99", L"{}");
        CHECK(result, "wide scan<int> should succeed");
        if (result) {
            CHECK(result->value() == 99, "wide scanned int should be 99");
        }
    }

    // 8. Range scanning: scan a std::vector<int> sequence (scn/ranges.h)
    //    (same usage as upstream ranges_test.cpp: "[123, 456]" with "{}")
    {
        auto result = scn::scan<std::vector<int>>("[123, 456]", "{}");
        CHECK(result, "scan<vector<int>> should succeed");
        if (result) {
            const auto& vec = result->value();
            CHECK(vec.size() == 2, "vector should have 2 elements");
            CHECK(vec[0] == 123 && vec[1] == 456,
                  "vector elements should be 123, 456");
        }
    }

    // 9. scan_int fast path (string_view -> int)
    {
        auto result = scn::scan_int<int>("  -255  ");
        CHECK(result, "scan_int should succeed");
        if (result) {
            CHECK(result->value() == -255, "scan_int should yield -255");
        }
    }

    if (failures != 0) {
        std::fprintf(stderr, "%d check(s) failed\n", failures);
        return 1;
    }
    std::printf("all scnlib consumer checks passed\n");
    return 0;
}
