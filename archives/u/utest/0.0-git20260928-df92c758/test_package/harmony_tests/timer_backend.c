#include <utest.h>
#include <errno.h>
#include <sys/utsname.h>

#if !defined(__OHOS__) || !defined(__aarch64__)
#error This test requires the real HarmonyOS aarch64 target.
#endif

UTEST(harmony, libc_timer_backend) {
    struct utsname platform;
    struct timespec wait_time={0,20000000};
    struct timespec before,after;
    utest_int64_t utest_before,utest_after;
    ASSERT_EQ(0,uname(&platform));
    ASSERT_STREQ("HarmonyOS",platform.sysname);
    ASSERT_STREQ("aarch64",platform.machine);
    ASSERT_EQ(TIME_UTC,timespec_get(&before,TIME_UTC));
    utest_before=utest_ns();
    while(nanosleep(&wait_time,&wait_time)!=0){ASSERT_EQ(EINTR,errno);}
    utest_after=utest_ns();
    ASSERT_EQ(TIME_UTC,timespec_get(&after,TIME_UTC));
    ASSERT_GT(utest_before,0);
    ASSERT_GE(utest_after-utest_before,10000000);
    ASSERT_GE(after.tv_sec,before.tv_sec);
    /* The framework's overflow-safe time conversion is part of this backend. */
    ASSERT_EQ(3000000000LL,utest_mul_div(3000000,1000000000,1000000));
}
UTEST_MAIN()
