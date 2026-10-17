#include <minunit.h>
#include <errno.h>

#if !defined(__OHOS__) || !defined(__aarch64__)
#error This test must use the real HarmonyOS aarch64 compiler target.
#endif

/* Exercise the library's selected OHOS libc timer backends, not a mock. */
MU_TEST(ohos_timer_backend) {
    double real_before = mu_timer_real();
    double cpu_before = mu_timer_cpu();
    struct timespec wait_time = {0, 20000000};
    while (nanosleep(&wait_time, &wait_time) != 0) {
        if (errno != EINTR) { mu_fail("OHOS nanosleep failed"); }
    }
    double real_after = mu_timer_real();
    double cpu_after = mu_timer_cpu();
    mu_assert(isfinite(real_before) && real_before > 0,
              "OHOS minunit real timer unavailable");
    mu_assert(isfinite(real_after) && real_after >= real_before + 0.010,
              "OHOS minunit real timer did not advance after nanosleep");
    mu_assert(isfinite(cpu_before) && cpu_before >= 0,
              "OHOS minunit process CPU timer unavailable");
    mu_assert(isfinite(cpu_after) && cpu_after >= cpu_before,
              "OHOS minunit process CPU timer regressed");
}

int main(void) {
    MU_RUN_TEST(ohos_timer_backend);
    MU_REPORT();
    return MU_EXIT_CODE;
}
