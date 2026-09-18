#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include <libmseed.h>

static int failures = 0;

#define CHECK(number, condition, message)                                 \
    do {                                                                  \
        if (condition) {                                                  \
            printf("ok %d - %s\n", number, message);                       \
        } else {                                                          \
            printf("not ok %d - %s\n", number, message);                   \
            failures++;                                                   \
        }                                                                 \
    } while (0)

int main(void) {
    /* 1. Library version matches the packaged upstream release. */
    CHECK(1, strcmp(LIBMSEED_VERSION, "2.19.8") == 0, "LIBMSEED_VERSION is 2.19.8");

    /* 2. MSRecord lifecycle: init returns a usable record, free clears it. */
    {
        MSRecord *msr = msr_init(NULL);
        int ok = (msr != NULL);
        if (ok) {
            msr_free(&msr);
            ok = (msr == NULL);
        }
        CHECK(2, ok, "msr_init/msr_free lifecycle");
    }

    /* 3. Trace-group lifecycle: init/free a group container. */
    {
        MSTraceGroup *group = mst_initgroup(NULL);
        int ok = (group != NULL);
        if (ok) {
            mst_freegroup(&group);
            ok = (group == NULL);
        }
        CHECK(3, ok, "mst_initgroup/mst_freegroup lifecycle");
    }

    /* 4. Time conversion round-trip through the high-precision time type. */
    {
        hptime_t hptime = ms_time2hptime(2022, 87, 12, 34, 56, 123456);
        BTime btime;
        memset(&btime, 0, sizeof(btime));
        int rc = ms_hptime2btime(hptime, &btime);
        int ok = (rc == 0 && btime.year == 2022 && btime.day == 87 &&
                  btime.hour == 12 && btime.min == 34 && btime.sec == 56);
        CHECK(4, ok, "ms_time2hptime/ms_hptime2btime round-trip");
    }

    /* 5. Sample-size lookup covers integer and ASCII sample types. */
    CHECK(5, ms_samplesize('i') == 4 && ms_samplesize('a') == 1,
          "ms_samplesize i==4 a==1");

    /* 6. Encoding name plus sample-rate factor/mult round-trip. */
    {
        int16_t factor = 0, multiplier = 0;
        int ok = (ms_encodingstr(DE_STEIM2) != NULL);
        if (ok) {
            ok = (ms_genfactmult(100.0, &factor, &multiplier) == 0);
        }
        if (ok) {
            double rate = ms_nomsamprate(factor, multiplier);
            ok = (rate > 99.0 && rate < 101.0);
        }
        CHECK(6, ok, "ms_encodingstr/ms_genfactmult/ms_nomsamprate");
    }

    if (failures == 0) {
        printf("test libmseed 2.19.8: OK (6/6 checks passed)\n");
    } else {
        printf("test libmseed 2.19.8: FAILED (%d failures)\n", failures);
    }
    return failures == 0 ? 0 : 1;
}
