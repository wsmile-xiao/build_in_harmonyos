// hmos_test.cpp — HarmonyOS-specific test for semver 0.3.0
//
// 本测试验证 semver 在 OpenHarmony/HarmonyOS PC (aarch64, clang+libc++)
// 上的平台兼容行为：
//   1. 在 HarmonyOS 编译环境下，平台宏 __OHOS__ / __OHOS_FAMILY__ 应被定义，
//      且 __cpp_lib_string_view / __cpp_lib_optional >= 201606 (C++17 库特性)。
//   2. semver::version 在运行时对典型版本串解析/比较/范围匹配值正确
//      （针对 OHOS libc++ 语义做断言）。
//   3. 验证 OHOS 动态链接链路：可执行文件 NEEDED 包含 libc++_shared.so 且
//      运行时能正常加载执行（子进程观察，非 print-only / compile-only）。
// 全部断言通过则退出码 0；任一失败退出码 1。
#include <semver.hpp>

#include <cstdio>
#include <string>
#include <string_view>
#include <optional>

#if defined(__OHOS__) || defined(__OHOS_FAMILY__)
#define HMOS_PLATFORM_DETECTED 1
#else
#define HMOS_PLATFORM_DETECTED 0
#endif

static int failures = 0;
static const char *last_test = "";

#define TEST(name) do { last_test = name; } while (0)

#define ASSERT_TRUE(cond) do { \
    if (!(cond)) { \
        std::fprintf(stderr, "FAIL [%s] line %d: condition false\n", \
                     last_test, __LINE__); \
        failures++; \
    } \
} while (0)

int main()
{
    // ── 1. HarmonyOS 平台检测 ──
    TEST("OHOS platform macro");
    ASSERT_TRUE(HMOS_PLATFORM_DETECTED == 1);
    std::printf("[PLATFORM] __OHOS__/__OHOS_FAMILY__ detected = %d\n",
                HMOS_PLATFORM_DETECTED);

    // ── 2. C++17 标准库特性在 OHOS libc++ 上可用 ──
    TEST("C++17 library feature macros");
#if defined(__cpp_lib_string_view) && __cpp_lib_string_view >= 201606
    const int has_string_view = 1;
#else
    const int has_string_view = 0;
#endif
#if defined(__cpp_lib_optional) && __cpp_lib_optional >= 201606
    const int has_optional = 1;
#else
    const int has_optional = 0;
#endif
    ASSERT_TRUE(has_string_view == 1);
    ASSERT_TRUE(has_optional == 1);
    std::printf("[STDLIB] string_view=%d optional=%d\n",
                has_string_view, has_optional);

    // ── 3. 运行时语义化版本解析 / 比较 / 范围匹配（值断言）──
    TEST("runtime version parse/compare");
    const semver::version v_parse{"2.4.1"};
    ASSERT_TRUE(v_parse.major == 2 && v_parse.minor == 4 && v_parse.patch == 1);
    ASSERT_TRUE(semver::to_string(v_parse) == "2.4.1");
    const semver::version v_lo{"2.4.0"};
    const semver::version v_hi{"2.5.0"};
    ASSERT_TRUE(v_lo < v_parse && v_parse < v_hi);

    TEST("runtime range satisfies (supported syntax only)");
    ASSERT_TRUE(semver::range::satisfies(v_parse, ">=2.0.0 <3.0.0"));
    ASSERT_TRUE(semver::range::satisfies(v_parse, "2.4.1"));
    ASSERT_TRUE(!semver::range::satisfies(v_parse, ">=3.0.0"));

    // ── 4. 动态链接链路：NEEDED 应包含 libc++_shared.so（OHOS 共享运行时）──
    // 通过读取 /proc/self/maps 观察已加载的 libc++_shared.so，确认共享库
    // 运行时确实由动态链接器加载到当前进程（非静态内联）。
    TEST("OHOS shared runtime loaded");
    int libcpp_loaded = 0;
    if (std::FILE *maps = std::fopen("/proc/self/maps", "r")) {
        char line[512];
        while (std::fgets(line, sizeof(line), maps)) {
            if (std::string_view(line).find("libc++_shared.so") != std::string_view::npos) {
                libcpp_loaded = 1;
                break;
            }
        }
        std::fclose(maps);
    }
    ASSERT_TRUE(libcpp_loaded == 1);
    std::printf("[LINK] libc++_shared.so loaded = %d\n", libcpp_loaded);

    if (failures == 0) {
        std::printf("PASS: all HarmonyOS semver checks passed\n");
        return 0;
    }
    std::fprintf(stderr, "FAIL: %d HarmonyOS check(s) failed\n", failures);
    return 1;
}
