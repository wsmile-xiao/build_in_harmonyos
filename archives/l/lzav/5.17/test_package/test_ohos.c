/*
 * lzav HarmonyOS-specific platform test.
 *
 * Verifies that the header-only library actually runs on the HarmonyOS PC
 * (OHOS) platform at runtime, not just that it compiles:
 *   1. Compiled with __OHOS__ defined (OHOS toolchain path)
 *   2. Runtime exposes a HarmonyOS kernel (uname sysname)
 *   3. Real compress/decompress round-trip on the OHOS consumer path
 */
#include <lzav.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/utsname.h>

static int check(int condition, const char *message) {
    if (!condition) {
        fprintf(stderr, "FAIL: %s\n", message);
        return 1;
    }
    printf("PASS: %s\n", message);
    return 0;
}

int main(void) {
#if !defined(__OHOS__)
    fprintf(stderr, "FAIL: test_ohos must be compiled for OpenHarmony (__OHOS__)\n");
    return 1;
#endif

    int failures = 0;
    struct utsname system_info;

    failures += check(uname(&system_info) == 0,
                      "HarmonyOS runtime exposes uname");
    if (failures == 0) {
        printf("INFO: uname sysname = %s, release = %s, machine = %s\n",
               system_info.sysname, system_info.release, system_info.machine);
        failures += check(strcmp(system_info.sysname, "HarmonyOS") == 0,
                          "runtime identifies as HarmonyOS");
    }

    /* Real round-trip through the public API on the OHOS path. */
    {
        const int src_len = 1 << 20;   /* 1 MiB */
        const int bound = lzav_compress_bound(src_len);
        unsigned char *src = (unsigned char *)malloc((size_t)src_len);
        unsigned char *comp = (unsigned char *)malloc((size_t)bound);
        unsigned char *decomp = (unsigned char *)malloc((size_t)src_len);
        int i, comp_len, dec_len;
        int rt_ok = 1;

        if (!src || !comp || !decomp) {
            fprintf(stderr, "FAIL: memory allocation on HarmonyOS\n");
            return 1;
        }
        for (i = 0; i < src_len; i++) {
            src[i] = (unsigned char)('a' + (i % 26));
            if (i % 2048 == 1024)
                src[i] ^= 0xC3;
        }

        comp_len = lzav_compress_default(src, comp, src_len, bound);
        failures += check(comp_len > 0 && comp_len < src_len,
                          "lzav_compress_default compresses on HarmonyOS");
        if (comp_len > 0) {
            dec_len = lzav_decompress(comp, decomp, comp_len, src_len);
            rt_ok = (dec_len == src_len) &&
                    (memcmp(src, decomp, (size_t)src_len) == 0);
            printf("INFO: comp_len=%d dec_len=%d (1 MiB round-trip)\n",
                   comp_len, dec_len);
        } else {
            rt_ok = 0;
        }
        failures += check(rt_ok, "round-trip equals source on HarmonyOS");

        free(src);
        free(comp);
        free(decomp);
    }

    if (failures == 0) {
        printf("PASS: lzav OK on OpenHarmony (%d checks)\n", 4);
        return 0;
    }
    printf("FAIL: %d lzav HarmonyOS checks failed\n", failures);
    return 1;
}