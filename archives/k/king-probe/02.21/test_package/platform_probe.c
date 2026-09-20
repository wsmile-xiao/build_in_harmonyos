/* Supplemental runtime checks for the platform used by Probe's PDB arithmetic. */
#include <errno.h>
#include <locale.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#if defined(EXPECT_OHOS) && !defined(__OHOS__)
#error OHOS target requires the compiler-provided __OHOS__ macro
#endif
#ifdef __OHOS__
#include <sys/utsname.h>
#endif

int main(void)
{
    char *end = NULL;
    char buffer[64];
    double coordinate;
    volatile double squared_distance = 6.76;

#ifdef __OHOS__
    struct utsname system;
    if (uname(&system) != 0 || strcmp(system.sysname, "HarmonyOS") != 0) {
        fputs("uname must identify the native HarmonyOS PC kernel\n", stderr);
        return 1;
    }
#if defined(__aarch64__)
    if (strcmp(system.machine, "aarch64") != 0) return 2;
#elif defined(__x86_64__)
    if (strcmp(system.machine, "x86_64") != 0) return 2;
#else
#error Unsupported HarmonyOS PC architecture
#endif
    printf("OHOS kernel=%s machine=%s\n", system.sysname, system.machine);
#endif

    /* These are actual libc/libm operations, not a platform success stub. */
    if (setlocale(LC_NUMERIC, "C") == NULL) return 3;
    errno = 0;
    coordinate = strtod("  -12.375", &end);
    if (errno != 0 || *end != '\0' || coordinate != -12.375) return 4;
    if (snprintf(buffer, sizeof(buffer), "%8.3f", coordinate) != 8 ||
        strcmp(buffer, " -12.375") != 0) return 5;
    if (fabs(sqrt(squared_distance) - 2.6) > 1e-12) return 6;
    errno = 0;
    coordinate = strtod("1e9999", &end);
    if (errno != ERANGE || !isinf(coordinate) || *end != '\0') return 7;
    puts("PDB numeric parsing, formatting, distance and overflow checks passed");
    return 0;
}
