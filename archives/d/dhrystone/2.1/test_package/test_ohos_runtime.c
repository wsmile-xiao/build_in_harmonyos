/* Verify the OHOS loader and process timing API used by Dhrystone. */
#ifndef __OHOS__
#error "This probe must be compiled with the HarmonyOS SDK"
#endif

#include <dlfcn.h>
#include <stdio.h>
#include <sys/auxv.h>
#include <sys/times.h>
#include <time.h>
#include <unistd.h>

int main(void)
{
    Dl_info info;
    struct tms usage;
    struct timespec cpu_time;
    long ticks = sysconf(_SC_CLK_TCK);
    if (sizeof(void *) != 8 || sizeof(time_t) != 8 || ticks <= 0)
        return 1;
    if (getauxval(AT_BASE) == 0 || dladdr((void *)clock_gettime, &info) == 0)
        return 2;
    if (info.dli_fname == NULL || info.dli_fname[0] == '\0')
        return 3;
    if (times(&usage) == (clock_t)-1 || usage.tms_utime < 0)
        return 4;
    if (clock_gettime(CLOCK_PROCESS_CPUTIME_ID, &cpu_time) != 0 || cpu_time.tv_nsec < 0)
        return 5;
    printf("OHOS_RUNTIME_OK ticks=%ld libc=%s time_t=%zu\n", ticks, info.dli_fname, sizeof(time_t));
    return 0;
}
