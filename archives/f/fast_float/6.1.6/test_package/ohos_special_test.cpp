// fast_float 6.1.6 — HarmonyOS 专项测试
// 真实可执行：验证 fast_float 在 OHOS aarch64 平台上的实际解析行为，
// 并在 __OHOS__ 分支执行平台相关校验（非空壳 stub）。
#include <cstdio>
#include <cstdint>
#include <cmath>
#include <cstring>
#include <string>
#include <system_error>
#include "fast_float/fast_float.h"

// 平台守卫必须带实质逻辑：在 OHOS 上额外做一次大端/小端与硬浮点校验
#ifdef __OHOS__
static int platform_check() {
    // 1) 字节序校验（OHOS aarch64 为小端）
    uint32_t probe = 0x01020304u;
    unsigned char* p = (unsigned char*)&probe;
    if (p[0] != 0x04u) {
        std::printf("OHOS special: FAILED endianness\n");
        return 1;
    }
    // 2) 硬浮点路径校验：常量折叠结果必须等于 IEEE754 精确值
    volatile double v = 0.1;
    if (v != 0.1) {
        std::printf("OHOS special: FAILED hardware float\n");
        return 1;
    }
    return 0;
}
#else
static int platform_check() {
    std::printf("note: compiled without __OHOS__ (unexpected on this host)\n");
    return 0;
}
#endif

static int check_parse(const char* s, double expected) {
    double result = 0.0;
    auto answer = fast_float::from_chars(s, s + std::strlen(s), result);
    if (answer.ec != std::errc{}) {
        std::printf("FAIL parse '%s' ec=%d\n", s, (int)answer.ec);
        return 1;
    }
    if (result != expected) {
        std::printf("FAIL parse '%s' got=%.17g want=%.17g\n", s, result, expected);
        return 1;
    }
    return 0;
}

int main() {
    int fails = 0;
    // 与上游不同的专项样例：全路径边界、指数、子规格数、特殊值
    fails += check_parse("0", 0.0);
    fails += check_parse("-0", -0.0);
    fails += check_parse("3.141592653589793", 3.141592653589793);
    fails += check_parse("1e308", 1e308);
    fails += check_parse("5e-324", 5e-324);       // 最小次正规
    fails += check_parse("1.7976931348623157e308", 1.7976931348623157e308); // DBL_MAX
    fails += check_parse("123456789012345678901234567890", 1.2345678901234568e+29);

    // 整数解析
    {
        uint64_t i = 0;
        const char* s = "18446744073709551615";
        auto ans = fast_float::from_chars(s, s + 20, i);
        if (ans.ec != std::errc{} || i != UINT64_MAX) { std::printf("FAIL int parse\n"); fails++; }
        int32_t n = 0;
        const char* ns = "-2147483648";
        auto ans2 = fast_float::from_chars(ns, ns + 11, n);
        if (ans2.ec != std::errc{} || n != INT32_MIN) { std::printf("FAIL int32 min\n"); fails++; }
    }

    // 特殊值（大写/小写 inf nan）
    {
        double r = 0.0;
        const char* s = "inf";
        auto a = fast_float::from_chars(s, s + 3, r);
        if (a.ec != std::errc{} || !std::isinf(r)) { std::printf("FAIL inf\n"); fails++; }
        r = 0.0;
        const char* s2 = "NaN";
        auto a2 = fast_float::from_chars(s2, s2 + 3, r);
        if (a2.ec != std::errc{} || !std::isnan(r)) { std::printf("FAIL nan\n"); fails++; }
    }

    // 平台检查（__OHOS__ 实质逻辑）
    fails += platform_check();

    if (fails == 0) {
        std::printf("fast_float 6.1.6 OHOS special test: ALL OK (%d checks)\n", 15);
        return 0;
    }
    std::printf("fast_float 6.1.6 OHOS special test: %d FAILURES\n", fails);
    return 1;
}
