// test_eabase — Conan L1 consumer test for eabase (EABase header-only).
// Uses only EABase's installed public headers and public types/macros to
// verify a third-party consumer can include and use the library normally.
//
// R02 补强：本文件真实断言覆盖补丁核心语义——
//   (1) 端序宏取值（EA_SYSTEM_LITTLE_ENDIAN 在 aarch64 Linux-family 必须定义，
//       运行时字节序与宏一致）；
//   (2) EA_PLATFORM_MIN_MALLOC_ALIGNMENT 在 aarch64 = 8（POSIX 风格条件
//       EA_PLATFORM_LINUX && EA_PROCESSOR_ARM64），且不大于实际 malloc 观测对齐；
//   (3) eastdarg.h va_list 引用传递路径：va_list_reference 在 aarch64 必须是
//       真实引用（va_list 为结构体 ABI），callee 推进后 caller 可见第二参数。

#include <EABase/eabase.h>
#include <EABase/earesult.h>
#include <EABase/eastdarg.h>
#include <EABase/eaunits.h>
#include <cstdio>
#include <cstdarg>
#include <cstdint>
#include <cstdlib>

static int gErrors = 0;

#define OH_CHECK(cond)                                                         \
    do {                                                                       \
        if (cond) std::printf("  [PASS] %s\n", #cond);                         \
        else { std::printf("  [FAIL] %s  (line %d)\n", #cond, __LINE__); ++gErrors; } \
    } while (0)

// va_list 引用推进：经 va_list_reference 传参，callee 的 va_arg 必须推进
// caller 的列表（aarch64 va_list 为 32 字节结构体，按值传递无法推进）。
static void ConsumeOne(va_list_reference args, int& out)
{
    out = va_arg(args, int);
}

static void TestVaListReferenceSemantics()
{
    struct Va2 {
        static void PushTwo(int& out1, int& out2, int marker, ...)
        {
            va_list l;
            va_start(l, marker);
            ConsumeOne(l, out1); // -> 17
            ConsumeOne(l, out2); // -> 99（引用推进必须生效）
            va_end(l);
        }
    };
    int a = 0, b = 0;
    Va2::PushTwo(a, b, 0, 17, 99);
    OH_CHECK(a == 17);
    OH_CHECK(b == 99);
}

int main()
{
    const char* result = "FAIL";
    std::printf("EABase %s consumer test\n", EA_PLATFORM_NAME);
    std::printf("EA_PLATFORM_DESCRIPTION: %s\n", EA_PLATFORM_DESCRIPTION);

    // ---- R02 (1)：端序宏取值与运行时字节序一致性 ----
    {
        int leDefined = 0;
#if defined(EA_SYSTEM_LITTLE_ENDIAN)
        leDefined = 1;
#endif
        OH_CHECK(leDefined == 1); // aarch64 Linux-family 必须定义小端宏
        std::uint32_t v = 0x12345678;
        std::uint8_t* p = reinterpret_cast<std::uint8_t*>(&v);
#if defined(EA_SYSTEM_LITTLE_ENDIAN)
        OH_CHECK(p[0] == 0x78); // 运行时字节序与小端宏一致
#elif defined(EA_SYSTEM_BIG_ENDIAN)
        OH_CHECK(p[0] == 0x12);
#endif
    }

    // ---- R02 (2)：EA_PLATFORM_MIN_MALLOC_ALIGNMENT 取值与 malloc 观测对齐 ----
    {
        int arm64 = 0;
#if defined(EA_PROCESSOR_ARM64)
        arm64 = 1;
#endif
        if (arm64) {
            OH_CHECK(EA_PLATFORM_MIN_MALLOC_ALIGNMENT == 8); // POSIX 条件设为 8
        } else {
            OH_CHECK(EA_PLATFORM_MIN_MALLOC_ALIGNMENT > 0);
        }
        // 实测 malloc 最小对齐不得低于宏声明（消费者自定义 allocator 的安全边界）
        std::size_t minObserved = 64;
        for (std::size_t size = 1; size <= 64; ++size) {
            for (int it = 0; it < 16; ++it) {
                void* q = std::malloc(size);
                std::size_t addr = reinterpret_cast<std::size_t>(q);
                std::size_t align = 64;
                do { if ((addr & (align - 1)) == 0) break; align >>= 1; } while (align > 1);
                if (align < minObserved) minObserved = align;
                std::free(q);
            }
        }
        OH_CHECK(EA_PLATFORM_MIN_MALLOC_ALIGNMENT <= minObserved);
    }

    // ---- R02 (3)：eastdarg.h va_list_reference 引用传递路径 ----
    TestVaListReferenceSemantics();

    // ---- 基础类型/宏冒烟（R01 保留） ----
    OH_CHECK(sizeof(int32_t) == 4 && sizeof(int64_t) == 8 && sizeof(char16_t) == 2);
    OH_CHECK(EA_SUCCEEDED(EA::EA_SUCCESS) && !EA_SUCCEEDED(EA::EA_FAILURE));
    OH_CHECK(EA_KILOBYTE(1) == 1000 && EA_MEBIBYTE(1) == (1024 * 1024));

    if (gErrors == 0) result = "PASS";
    std::printf("EABase consumer test result: %s (errors=%d)\n", result, gErrors);
    return gErrors;
}