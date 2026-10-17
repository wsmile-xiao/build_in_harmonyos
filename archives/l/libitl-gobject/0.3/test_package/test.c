/*
 * Consumer test for libitl-gobject 0.3.
 *
 * Exercises the public GObject layer over libitl through the Conan-generated
 * CMakeDeps target `libitl-gobject::libitl-gobject`: Gregorian/Hijri
 * conversion, the ItlPrayer GObject lifecycle, location/method setup, prayer
 * times, next-day Fajr and the Qibla direction.
 *
 * Argument-order note (verified against libitl 0.8.0, see notes.md): the ITL
 * entry points take (day, month, year) positionally even where the C parameter
 * names in hijri.h say otherwise, and libitl-gobject forwards them unchanged.
 * The gtk-doc blocks of itl_G2H / itl_H2G / itl_HijriGreg list @dg / @dh first,
 * which matches the implementation. Every golden value below was measured on
 * the packaged library, so a mismatch means the port regressed.
 */
#include <math.h>
#include <stdio.h>

#include <glib.h>
#include <glib-object.h>

#include <itl-gobject.h>

static int failures = 0;
static int assertions = 0;

#define CHECK(cond, ...)                                        \
    do {                                                        \
        assertions++;                                           \
        if (cond) {                                             \
            printf("ok   - ");                                  \
        } else {                                                \
            printf("FAIL - ");                                  \
            failures++;                                         \
        }                                                       \
        printf(__VA_ARGS__);                                    \
        printf("\n");                                           \
    } while (0)

static gboolean date_is(GDate *date, guint year, guint month, guint day)
{
    return date != NULL && g_date_valid(date) &&
           g_date_get_year(date) == year &&
           g_date_get_month(date) == month &&
           g_date_get_day(date) == day;
}

int main(void)
{
    GDate *hijri = NULL;
    GDate *greg = NULL;
    GDate *converted = NULL;
    GDate *sample = NULL;
    ItlPrayer *prayer = NULL;
    GList *times = NULL;
    GList *item = NULL;
    GDateTime *next_fajr = NULL;
    gdouble qibla;
    guint count;
    guint index;
    gint previous_hour = -1;

    /* ---- Gregorian -> Hijri via the Umm al-Qura algorithm ---- */
    hijri = itl_G2H(28, 7, 2026);
    CHECK(hijri != NULL, "itl_G2H(2026-07-28) returns a date");
    CHECK(hijri != NULL && g_date_valid(hijri), "G2H result is a valid GDate");
    CHECK(date_is(hijri, 1448, 2, 14),
          "G2H(2026-07-28) == 1448-02-14 (got %04d-%02d-%02d)",
          hijri ? (int) g_date_get_year(hijri) : 0,
          hijri ? (int) g_date_get_month(hijri) : 0,
          hijri ? (int) g_date_get_day(hijri) : 0);

    /* ---- round trip back to Gregorian ---- */
    greg = itl_H2G(14, 2, 1448);
    CHECK(greg != NULL, "itl_H2G(1448-02-14) returns a date");
    CHECK(date_is(greg, 2026, 7, 28),
          "H2G(G2H(2026-07-28)) round trips to 2026-07-28 (got %04d-%02d-%02d)",
          greg ? (int) g_date_get_year(greg) : 0,
          greg ? (int) g_date_get_month(greg) : 0,
          greg ? (int) g_date_get_day(greg) : 0);

    /* ---- itl_h_date: Gregorian input -> Hijri output (tabular) ---- */
    converted = itl_h_date(28, 7, 2026);
    CHECK(converted != NULL && g_date_valid(converted),
          "itl_h_date(2026-07-28) returns a valid date");
    CHECK(converted != NULL && g_date_get_year(converted) == 1448 &&
              g_date_get_month(converted) == 2,
          "itl_h_date(2026-07-28) lands in Hijri 1448-02 (got %04d-%02d)",
          converted ? (int) g_date_get_year(converted) : 0,
          converted ? (int) g_date_get_month(converted) : 0);
    if (converted != NULL) {
        g_date_free(converted);
        converted = NULL;
    }

    /* ---- itl_g_date: Hijri input -> Gregorian output (tabular) ---- */
    converted = itl_g_date(14, 2, 1448);
    CHECK(converted != NULL && g_date_valid(converted),
          "itl_g_date(1448-02-14) returns a valid date");
    CHECK(converted != NULL && g_date_get_year(converted) == 2026 &&
              g_date_get_month(converted) == 7,
          "itl_g_date(1448-02-14) lands in Gregorian 2026-07 (got %04d-%02d)",
          converted ? (int) g_date_get_year(converted) : 0,
          converted ? (int) g_date_get_month(converted) : 0);
    if (converted != NULL) {
        g_date_free(converted);
        converted = NULL;
    }

    /* ---- itl_HijriGreg dispatcher, Umm al-Qura branch both ways ---- */
    sample = g_date_new_dmy(28, 7, 2026);
    converted = itl_HijriGreg(sample, FALSE, TRUE);
    CHECK(converted != NULL && g_date_valid(converted),
          "itl_HijriGreg(Gregorian, UmmAlQura) returns a valid date");
    CHECK(date_is(converted, 1448, 2, 14),
          "itl_HijriGreg(Gregorian 2026-07-28, UmmAlQura) == 1448-02-14");
    if (converted != NULL) {
        g_date_free(converted);
        converted = NULL;
    }
    if (sample != NULL) {
        g_date_free(sample);
        sample = NULL;
    }

    sample = g_date_new_dmy(14, 2, 1448);
    converted = itl_HijriGreg(sample, TRUE, TRUE);
    CHECK(converted != NULL && g_date_valid(converted),
          "itl_HijriGreg(Hijri, UmmAlQura) returns a valid date");
    CHECK(date_is(converted, 2026, 7, 28),
          "itl_HijriGreg(Hijri 1448-02-14, UmmAlQura) == 2026-07-28");
    if (converted != NULL) {
        g_date_free(converted);
        converted = NULL;
    }
    if (sample != NULL) {
        g_date_free(sample);
        sample = NULL;
    }

    /* ---- ItlPrayer GObject ---- */
    CHECK(itl_prayer_get_type() != G_TYPE_INVALID,
          "itl_prayer_get_type() registers a GType");
    prayer = itl_prayer_new();
    CHECK(prayer != NULL, "itl_prayer_new() returns an instance");
    CHECK(prayer != NULL && GOBJECT_IS_PRAYER(prayer),
          "instance satisfies GOBJECT_IS_PRAYER()");

    if (prayer != NULL) {
        gdouble qibla_min;
        gdouble qibla_max;

        /* Abu Dhabi: 54.3667E, 24.4667N, UTC+4 — setLocation takes (lon, lat) */
        itl_prayer_setLocation(prayer, 54.3667, 24.4667, 4.0, FALSE);
        itl_prayer_setMethod(prayer, UMM_ALQURRA);
        CHECK(1, "setLocation/setMethod accepted");

        qibla = itl_prayer_getNorthQibla(prayer);
        printf("info - Qibla from Abu Dhabi: %.3f deg\n", qibla);
        qibla_min = 98.9;
        qibla_max = 100.9;
        CHECK(qibla >= 0.0 && qibla < 360.0,
              "Qibla is an angle in [0, 360) (got %.3f)", qibla);
        /* The great-circle azimuth from Abu Dhabi to the Kaaba is 260.1 deg
         * clockwise from north; ITL reports the complementary angle counted
         * the other way round, so 360 - 260.1 = 99.9 deg. */
        CHECK(qibla > qibla_min && qibla < qibla_max,
              "Qibla from Abu Dhabi == 99.9 deg in ITL's convention (got %.3f)",
              qibla);

        /* ---- prayer times for a fixed date ---- */
        sample = g_date_new_dmy(3, 9, 2014);
        times = itl_prayer_getPrayerTimes(prayer, sample);
        count = g_list_length(times);
        CHECK(count == 6, "getPrayerTimes returns 6 entries (got %u)", count);

        for (item = times, index = 0; item != NULL; item = item->next, index++) {
            GDateTime *moment = (GDateTime *) item->data;
            gint hour;

            CHECK(moment != NULL, "prayer time %u is a non-NULL entry", index);
            if (moment == NULL) {
                continue;
            }
            hour = g_date_time_get_hour(moment);
            CHECK(hour >= 0 && hour <= 23,
                  "prayer time %u hour within 0..23 (got %d)", index, hour);
            CHECK(hour >= previous_hour,
                  "prayer times are ordered Fajr..Isha (entry %u hour %d >= %d)",
                  index, hour, previous_hour);
            previous_hour = hour;
            g_date_time_unref(moment);
        }
        g_list_free(times);
        times = NULL;

        CHECK(previous_hour > 0,
              "prayer times span the day (last hour %d)", previous_hour);

        /* ---- next-day Fajr ---- */
        next_fajr = itl_prayer_getNextDayFajr(prayer, sample);
        CHECK(next_fajr != NULL, "getNextDayFajr returns a GDateTime");
        if (next_fajr != NULL) {
            g_date_time_unref(next_fajr);
            next_fajr = NULL;
        }
        if (sample != NULL) {
            g_date_free(sample);
            sample = NULL;
        }

        g_object_unref(prayer);
        prayer = NULL;
    }

    if (hijri != NULL) {
        g_date_free(hijri);
    }
    if (greg != NULL) {
        g_date_free(greg);
    }

    printf("---\n%d assertion(s), %d failure(s)\n", assertions, failures);
    if (failures != 0) {
        fprintf(stderr, "%d assertion(s) failed\n", failures);
        return 1;
    }
    printf("test libitl-gobject 0.3: OK\n");
    return 0;
}
