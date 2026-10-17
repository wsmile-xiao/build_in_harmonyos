#include <stdio.h>

int main(void)
{
#if !defined(__OHOS__)
    fprintf(stderr, "FAIL: __OHOS__ is not defined\n");
    return 1;
#endif

#if !defined(__aarch64__)
    fprintf(stderr, "FAIL: target is not AArch64\n");
    return 1;
#endif

    if (sizeof(void *) != 8) {
        fprintf(stderr, "FAIL: pointer size is %zu, expected 8\n",
                sizeof(void *));
        return 1;
    }

    printf("OHOS_PLATFORM_TEST_OK: OHOS AArch64 64-bit\n");
    return 0;
}
