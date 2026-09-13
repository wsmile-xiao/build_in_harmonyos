/* Consumer test for datefudge's LD_PRELOAD time interposition. */

#include <stdio.h>
#include <stdlib.h>
#include <sys/time.h>
#include <time.h>

#ifdef DATEFUDGE_EXPECT_OHOS
#ifndef __OHOS__
#error "HarmonyOS test must be compiled with the OHOS toolchain"
#endif
#ifdef __GLIBC__
#error "HarmonyOS test must not use the glibc C library"
#endif
#endif

static int expect_seconds(const char *name, time_t actual, time_t expected)
{
    if (actual == expected) {
        return 0;
    }
    fprintf(stderr, "%s: got %lld, expected %lld\n",
            name, (long long)actual, (long long)expected);
    return 1;
}

int main(void)
{
    const char *value = getenv("DATEFUDGE_EXPECTED");
    struct timeval tv;
    struct timespec realtime;
    struct timespec monotonic;
    time_t stored = 0;
    time_t returned;
    time_t expected;
    int failures = 0;

    if (value == NULL || value[0] == '\0') {
        fputs("DATEFUDGE_EXPECTED is not set\n", stderr);
        return 1;
    }
    expected = (time_t)strtoll(value, NULL, 10);

    returned = time(&stored);
    failures += expect_seconds("time return", returned, expected);
    failures += expect_seconds("time output", stored, expected);

    if (gettimeofday(&tv, NULL) != 0) {
        perror("gettimeofday");
        return 1;
    }
    failures += expect_seconds("gettimeofday", tv.tv_sec, expected);
    if (tv.tv_usec != 0) {
        fprintf(stderr, "gettimeofday subseconds: got %ld, expected 0\n",
                (long)tv.tv_usec);
        failures++;
    }

    if (clock_gettime(CLOCK_REALTIME, &realtime) != 0) {
        perror("clock_gettime realtime");
        return 1;
    }
    failures += expect_seconds("clock_gettime realtime", realtime.tv_sec, expected);
    if (realtime.tv_nsec != 0) {
        fprintf(stderr, "clock_gettime subseconds: got %ld, expected 0\n",
                realtime.tv_nsec);
        failures++;
    }

    if (clock_gettime(CLOCK_MONOTONIC, &monotonic) != 0) {
        perror("clock_gettime monotonic");
        return 1;
    }
    if (monotonic.tv_sec == expected) {
        fputs("CLOCK_MONOTONIC was incorrectly modified\n", stderr);
        failures++;
    }

    if (failures != 0) {
        return 1;
    }
    puts("datefudge time/gettimeofday/clock_gettime interposition passed");
    return 0;
}
