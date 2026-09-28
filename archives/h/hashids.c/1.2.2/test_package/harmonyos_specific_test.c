/* hashids.c 1.2.2 — HarmonyOS-specific test (r03)
 * 在 OHOS (aarch64) 工具链下编译运行，验证:
 *   1) 平台宏 __OHOS__ 与 __aarch64__ 已定义（确认目标为 HarmonyOS aarch64 平台）;
 *   2) hashids 公开 API 在 OHOS 设备上真实调用并有可观察结果
 *      （自定义 salt 编码 -> then 解码往返一致，含边界值 0 与 ULLONG_MAX）。
 */
#include <stdio.h>
#include <string.h>
#include <limits.h>
#include <hashids.h>

#if !defined(__OHOS__)
#error "harmonyos_specific_test: __OHOS__ not defined — not compiled for HarmonyOS platform"
#endif
#if !defined(__aarch64__)
#error "harmonyos_specific_test: __aarch64__ not defined — not HarmonyOS aarch64 target"
#endif

int
main(void)
{
    hashids_t *h = hashids_init2("ohos-device-salt", 6);
    if (h == NULL) {
        printf("FAIL: hashids_init2\n");
        return 1;
    }

    /* 边界值：0 与 ULLONG_MAX 编码后解码往返必须一致 */
    unsigned long long nums[3] = {0ull, 18446744073709551615ull, 42ull};
    char buf[256];
    size_t n = hashids_encode(h, buf, 3, nums);
    if (n == 0) {
        printf("FAIL: hashids_encode\n");
        return 2;
    }
    buf[n] = '\0';

    unsigned long long out[4];
    size_t r = hashids_decode(h, buf, out, 4);
    if (r != 3 || out[0] != 0ull || out[1] != 18446744073709551615ull ||
        out[2] != 42ull) {
        printf("FAIL: roundtrip r=%zu got %llu,%llu,%llu\n",
            r, out[0], out[1], out[2]);
        return 3;
    }

    /* 平台实测：hashids_numbers_count 同 roundtrip 一致性 */
    if (hashids_numbers_count(h, buf) != 3) {
        printf("FAIL: hashids_numbers_count\n");
        return 4;
    }

    hashids_free(h);
    printf("harmonyos_specific_test OK: platform=OHOS(aarch64) __OHOS__/__aarch64__ defined, "
           "hashids encode/decode roundtrip on device passed (0, ULLONG_MAX, 42)\n");
    return 0;
}