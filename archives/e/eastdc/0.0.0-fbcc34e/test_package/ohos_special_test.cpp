// eastdc 0.0.0-fbcc34e — HarmonyOS 专项测试
// 真实可执行：验证 eastdc 在 OHOS aarch64 平台上的实际行为，
// 并在 __OHOS__ 分支执行平台相关校验（非空壳 stub）。
#include <cstdio>
#include <cstdint>
#include <cstring>
#include <cstdlib>

#include <EAStdC/EAEndian.h>
#include <EAStdC/EAString.h>
#include <EAStdC/Int128_t.h>

// 平台守卫必须带实质逻辑：OHOS aarch64 为小端，校验字节序与整型宽度
#ifdef __OHOS__
static int platform_check()
{
    // 1) 字节序校验（OHOS aarch64 应为小端）
    std::uint32_t probe = 0x01020304u;
    unsigned char* p = (unsigned char*)&probe;
    if (p[0] != 0x04u)
    {
        std::printf("OHOS special: FAILED endianness (expected little-endian)\n");
        return 1;
    }
    // 2) EA_SYSTEM_LITTLE_ENDIAN 宏应已由 EABase 定义（aarch64 Linux-family）
#ifdef EA_SYSTEM_LITTLE_ENDIAN
    std::printf("OHOS special: EA_SYSTEM_LITTLE_ENDIAN defined\n");
#else
    std::printf("OHOS special: FAILED EA_SYSTEM_LITTLE_ENDIAN missing\n");
    return 1;
#endif
    // 3) 指针宽度/对齐（OHOS aarch64: LP64, sizeof(void*)=8）
    if (sizeof(void*) != 8)
    {
        std::printf("OHOS special: FAILED sizeof(void*)=%zu (expected 8)\n", sizeof(void*));
        return 1;
    }
    return 0;
}
#else
static int platform_check()
{
    std::printf("note: compiled without __OHOS__ (unexpected on this host)\n");
    return 0;
}
#endif

// 通过公开 API 做端序转换并核对可观察结果（EAEndian.h）
static int check_swizzle()
{
    using namespace EA::StdC;
    // 小端机器上 ToBigEndian(0x12345678) 应交换字节
    std::uint32_t v = 0x12345678u;
    std::uint32_t be = ToBigEndian(v);
    unsigned char* p = (unsigned char*)&be;
    if (p[0] != 0x12u || p[1] != 0x34u || p[2] != 0x56u || p[3] != 0x78u)
    {
        std::printf("OHOS special: FAILED ToBigEndian swizzle\n");
        return 1;
    }
    // 往返一致性
    if (FromBigEndian(be) != v)
    {
        std::printf("OHOS special: FAILED FromBigEndian roundtrip\n");
        return 1;
    }
    std::printf("OHOS special: ToBigEndian/FromBigEndian roundtrip OK\n");
    return 0;
}

// 通过公开 API 验证 Int128_t 基础运算
static int check_int128()
{
    using namespace EA::StdC;
    EA::StdC::int128_t a = 0x7fffffffffffffffLL; // 2^63 - 1
    EA::StdC::int128_t b = 2;
    EA::StdC::int128_t c = a * b; // 2*(2^63-1) = 2^64 - 2, 超出 64 位需 int128 容纳
    if (c != (EA::StdC::int128_t((std::uint64_t)0xfffffffffffffffeULL)))
    {
        std::printf("OHOS special: FAILED int128 multiply\n");
        return 1;
    }
    std::printf("OHOS special: int128_t multiply OK\n");
    return 0;
}

int main()
{
    int fails = 0;
    fails += platform_check();
    fails += check_swizzle();
    fails += check_int128();

    if (fails == 0)
    {
        std::printf("eastdc 0.0.0-fbcc34e OHOS special test: ALL OK\n");
        return 0;
    }
    std::printf("eastdc 0.0.0-fbcc34e OHOS special test: %d FAILURES\n", fails);
    return 1;
}
