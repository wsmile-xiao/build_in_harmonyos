#include <stdio.h>
#include <string.h>

#include "kal.h"

static int failures;

#define CHECK(condition)                                                      \
    do {                                                                      \
        if (!(condition)) {                                                   \
            fprintf(stderr, "CHECK failed: %s at line %d\n",                \
                    #condition, __LINE__);                                    \
            ++failures;                                                       \
        }                                                                     \
    } while (0)

static void test_gregorian(void)
{
    int day, month, year;
    long jd = kal_conv_gre_jd(1, 1, 2000);
    CHECK(jd == 2451545);
    kal_conv_jd_gre(jd, &day, &month, &year);
    CHECK(day == 1 && month == 1 && year == 2000);
}

static void test_julian(void)
{
    int day, month, year;
    long jd = kal_conv_jul_jd(1, 1, 2000);
    kal_conv_jd_jul(jd, &day, &month, &year);
    CHECK(day == 1 && month == 1 && year == 2000);
}

static void test_arabic(void)
{
    int day, month, year;
    long jd = kal_conv_ar_jd(1, 1, 1445);
    kal_conv_jd_ar(jd, &day, &month, &year);
    CHECK(day == 1 && month == 1 && year == 1445);
}

static void test_jewish(void)
{
    int day, month, year;
    long jd = kal_conv_jew_jd(1, 1, 5784);
    kal_conv_jd_jew(jd, &day, &month, &year);
    CHECK(day == 1 && month == 1 && year == 5784);
    CHECK(kal_jew_leap(5784) == 1);
}

static void test_generic_dispatch(void)
{
    static const int dates[4][3] = {
        {15, 3, 2000}, {15, 3, 2000}, {15, 3, 1420}, {15, 3, 5784}
    };
    int system;
    for (system = 0; system < KAL_XXX; ++system) {
        int day, month, year;
        long jd = kal_conv_xxx_jd(
            dates[system][0], dates[system][1], dates[system][2], system);
        kal_conv_jd_xxx(jd, &day, &month, &year, system);
        CHECK(day == dates[system][0]);
        CHECK(month == dates[system][1]);
        CHECK(year == dates[system][2]);
    }
}

static void test_validation(void)
{
    long jd = 0;
    CHECK(kal_gre_check(&jd, 29, 2, 2000) == 0);
    CHECK(jd == kal_conv_gre_jd(29, 2, 2000));
    CHECK(kal_gre_check(&jd, 29, 2, 1900) != 0);
    CHECK(kal_general_check(0, 1, 2000) != 0);
}

static void test_weekday_helpers(void)
{
    long saturday = 2451545;
    long next_saturday = kal_next_after_dw(saturday, 6);
    long previous_saturday = kal_prev_before_dw(saturday, 6);
    CHECK(kal_day_of_week(saturday) == 6);
    CHECK(next_saturday == saturday + 7);
    CHECK(previous_saturday == saturday - 7);
    CHECK(kal_next_dw(saturday, 6) == saturday);
    CHECK(kal_prev_dw(saturday, 6) == saturday);
}

static void test_metadata_and_easter(void)
{
    int day, month, year;
    long easter = kal_gre_east(2000);
    CHECK(strcmp(kal_proc_get_name(KAL_GRE), "gre") == 0);
    CHECK(strcmp(kal_ar_months(9), "Ramadan") == 0);
    CHECK(strcmp(kal_jew_months(1), "Tishri") == 0);
    CHECK(kal_proc_valid(KAL_PROCS_EAST, KAL_GRE) == 0);
    CHECK(kal_proc_valid(KAL_PROCS_EAST, KAL_AR) != 0);
    kal_conv_jd_gre(easter, &day, &month, &year);
    CHECK(day == 23 && month == 4 && year == 2000);
}

int main(void)
{
    test_gregorian();
    test_julian();
    test_arabic();
    test_jewish();
    test_generic_dispatch();
    test_validation();
    test_weekday_helpers();
    test_metadata_and_easter();

    if (failures != 0) {
        fprintf(stderr, "libkal consumer test: %d checks failed\n", failures);
        return 1;
    }
    puts("libkal consumer test: 8 functional groups passed");
    return 0;
}
