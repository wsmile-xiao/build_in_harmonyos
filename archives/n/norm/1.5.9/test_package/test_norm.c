/*
 * test_norm.c — test_package consumer for the `norm` package (R34).
 *
 * Exercises the real NRL NORM API shipped in normApi.h:
 *   1. NormGetVersion()          — queries the library version triple
 *   2. NormCreateInstance()      — allocates + starts a NORM protocol engine
 *   3. NormDestroyInstance()     — tears the engine down again
 * and verifies the returned handles/version are sane.  This proves the
 * consumer can link against the packaged libnorm and call into it at
 * runtime (not just a print-only smoke test).
 */
#include <normApi.h>
#include <stdio.h>

int main(void)
{
    int major = 0, minor = 0, patch = 0;
    NormGetVersion(&major, &minor, &patch);
    printf("norm version: %d.%d.%d\n", major, minor, patch);
    if (major != 1 || minor != 5)
    {
        printf("FAIL: unexpected NORM version %d.%d.%d\n", major, minor, patch);
        return 1;
    }

    NormInstanceHandle inst = NormCreateInstance();
    if (inst == NORM_INSTANCE_INVALID)
    {
        printf("FAIL: NormCreateInstance() returned invalid handle\n");
        return 1;
    }
    printf("norm instance created OK\n");

    NormDestroyInstance(inst);
    printf("norm instance destroyed OK\n");
    printf("test_norm: PASS\n");
    return 0;
}
