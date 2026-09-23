/*
 * test_package / test.cpp — icu/76.1 consumer test (R34: must call real API).
 *
 * Exposes the C API of ICU through the three packaged static libraries
 * (libicuuc / libicui18n / libicudata) and asserts actual behavior, so a
 * broken/empty package cannot pass:
 *
 *   - u_getVersion       (libicuuc):  library reports a plausible ICU version
 *   - ucol_open/strcoll  (libicuuc):  real collation comparison
 *   - ucal_open/get      (libicui18n): real calendar day-of-week lookup
 *
 * The package is built with --enable-renaming, so every exported symbol
 * carries a version suffix. urename.h (pulled in transitively by
 * the unicode headers through unicode/umachine.h) maps the plain source-level
 * names to the suffixed symbols, so the calls below link unchanged.
 *
 * Exit code: 0 = all assertions pass, 1 = at least one assertion failed.
 */

#include <stdio.h>
#include <string.h>

#include <unicode/ucol.h>
#include <unicode/ucal.h>
#include <unicode/utypes.h>
#include <unicode/uversion.h>

static int g_failures = 0;
static int g_checks = 0;

#define CHECK(cond, msg)                                              \
    do {                                                              \
        g_checks++;                                                   \
        if (!(cond)) {                                                \
            fprintf(stderr, "  [FAIL] %s (line %d)\n", msg, __LINE__); \
            g_failures++;                                             \
        } else {                                                      \
            fprintf(stderr, "  [PASS] %s\n", msg);                    \
        }                                                             \
    } while (0)

int main(void)
{
    UErrorCode status = U_ZERO_ERROR;

    /* --- 1. Version (libicuuc / icudata) --- */
    UVersionInfo ver = { 0, 0, 0, 0 }; /* uint8_t[4] */
    u_getVersion(ver);
    fprintf(stderr, "  ICU version = %u.%u.%u.%u\n", ver[0], ver[1], ver[2], ver[3]);
    CHECK(ver[0] >= 76, "u_getVersion: major version >= 76");

    /* --- 2. Collation (libicuuc): ucol_strcoll --- */
    UCollator *coll = ucol_open("en", &status);
    CHECK(U_SUCCESS(status) && coll != NULL, "ucol_open(\"en\") succeeds");
    if (coll != NULL) {
        const UChar foo[] = { 'F', 'o', 'o' }; /* "Foo" */
        const UChar bar[] = { 'B', 'a', 'r' }; /* "Bar" */
        const UChar foo2[] = { 'f', 'o', 'o' }; /* "foo" (lower case) */
        UCollationResult r_gt = ucol_strcoll(coll, foo, 3, bar, 3); /* Foo > Bar */
        UCollationResult r_lt = ucol_strcoll(coll, bar, 3, foo, 3); /* Bar < Foo */
        UCollationResult r_eq = ucol_strcoll(coll, foo2, 3, foo, 3); /* foo vs Foo: root equal on case-insensitive? en is case-sensitive -> not equal */
        fprintf(stderr, "  ucol_strcoll(Foo,Bar)=%d (Bar,Foo)=%d (foo,Foo)=%d\n",
                (int)r_gt, (int)r_lt, (int)r_eq);
        CHECK(r_gt == UCOL_GREATER, "ucol_strcoll(Foo, Bar) == UCOL_GREATER");
        CHECK(r_lt == UCOL_LESS, "ucol_strcoll(Bar, Foo) == UCOL_LESS");
        CHECK(r_eq != UCOL_EQUAL, "ucol_strcoll(foo, Foo) != UCOL_EQUAL (case-sensitive root)");
        ucol_close(coll);
    }

    /* --- 3. Calendar (libicui18n): day-of-week lookup --- */
    /* ICU 76.1: ucal_open(zoneID, len, locale, type, status) — 5 params.
     * NULL zoneID => default time zone; len -1 => null-terminated. */
    UCalendar *cal = ucal_open(NULL, -1, "en-US", UCAL_GREGORIAN, &status);
    CHECK(U_SUCCESS(status) && cal != NULL, "ucal_open(\"en-US\", GREGORIAN) succeeds");
    if (cal != NULL) {
        /* 2024-01-01 was a Monday.
         * ICU 76.1: ucal_set(cal, field, value) — 3 params (no UErrorCode). */
        ucal_set(cal, UCAL_ERA, 1);
        ucal_set(cal, UCAL_YEAR, 2024);
        ucal_set(cal, UCAL_MONTH, 0); /* January = 0 */
        ucal_set(cal, UCAL_DAY_OF_MONTH, 1);
        int dow = ucal_get(cal, UCAL_DAY_OF_WEEK, &status);
        int day = ucal_get(cal, UCAL_DAY_OF_MONTH, &status);
        fprintf(stderr, "  2024-01-01 -> day_of_week=%d day_of_month=%d\n", dow, day);
        CHECK(U_SUCCESS(status), "ucal_get(UCAL_DAY_OF_WEEK) succeeds");
        CHECK(dow == UCAL_MONDAY, "2024-01-01 is a Monday");
        CHECK(day == 1, "day_of_month round-trips to 1");
        ucal_close(cal);
    }

    /* --- summary --- */
    fprintf(stderr, "\n  %d/%d assertions passed\n", g_checks - g_failures, g_checks);
    if (g_failures != 0) {
        fprintf(stderr, "TEST FAILED: %d assertion(s) failed\n", g_failures);
        return 1;
    }
    fprintf(stderr, "test icu 76.1: OK (%d assertions)\n", g_checks);
    return 0;
}
