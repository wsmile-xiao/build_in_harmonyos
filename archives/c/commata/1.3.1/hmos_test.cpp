// hmos_test.cpp — HarmonyOS-specific test for commata 1.3.1
//
// 本测试验证 commata 在 OpenHarmony/HarmonyOS PC (aarch64, clang+libc++)
// 上的平台兼容行为：
//   1. 在 HarmonyOS 编译环境下，平台宏 __OHOS__ / __OHOS_FAMILY__ 应被定义，
//      且 C++17 库特性宏（__cpp_lib_string_view 等）可用。
//   2. commata 的 parse_csv + table_pull 在运行时对典型 CSV 输入解析出
//      正确的字段序列（针对 OHOS libc++ 语义做断言，含 SSO 短串与堆串
//      两种输入长度）。
//   3. 验证 OHOS 动态链接链路：可执行文件运行时所依赖的 libc++_shared.so
//      确实由动态链接器加载到当前进程（非静态内联）。
// 全部断言通过则退出码 0；任一失败退出码 1。
#include <commata/parse_csv.hpp>
#include <commata/parse_tsv.hpp>
#include <commata/table_pull.hpp>

#include <cstdio>
#include <string>
#include <string_view>

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
        std::fprintf(stderr, "FAIL: %s: %s (line %d)\n", \
                     last_test, #cond, __LINE__); \
        ++failures; \
    } \
} while (0)

// Collect fields via table_pull; return field count and fill first/last.
static int collect_fields(const std::string &csv,
                          std::string *first, std::string *last)
{
    auto pull = commata::make_table_pull(
        commata::make_csv_source(csv), std::size_t(64));
    int count = 0;
    while (pull()) {
        if (pull->size() > 0) {
            ++count;
            if (count == 1) {
                first->assign(pull->data(), pull->size());
            }
            last->assign(pull->data(), pull->size());
        }
    }
    return count;
}

int main()
{
    // ── 1. 平台与语言特性检测 ──
    TEST("OHOS platform macro");
    ASSERT_TRUE(HMOS_PLATFORM_DETECTED == 1);
#if defined(__cpp_lib_string_view) && __cpp_lib_string_view >= 201606
    TEST("C++17 string_view feature macro");
    ASSERT_TRUE(1);
#else
    TEST("C++17 string_view feature macro");
    ASSERT_TRUE(0);
#endif

    // ── 2. 运行时解析功能（SSO 短串 ≤ 22 字符 + 堆串两种路径）──
    {
        TEST("parse SSO short CSV via table_pull");
        std::string first, last;
        const int n = collect_fields(std::string("X,Y\n1,2\n"), &first, &last);
        ASSERT_TRUE(n == 4);
        ASSERT_TRUE(first == "X");
        ASSERT_TRUE(last == "2");
    }
    {
        TEST("parse heap-allocated CSV via table_pull");
        // 头行长于 libc++ SSO 阈值（22 字符），确保字符串走堆分配路径
        std::string csv = "Column000000000000001,Column000000000000002\n"
                          "alpha,beta\n";
        std::string first, last;
        const int n = collect_fields(csv, &first, &last);
        ASSERT_TRUE(n == 4);
        ASSERT_TRUE(first == "Column000000000000001");
        ASSERT_TRUE(last == "beta");
    }
    {
        TEST("TSV via parse_tsv on owned input");
        auto pull = commata::make_table_pull(
            commata::make_tsv_source(std::string("A\tB\n1\t2\n")),
            std::size_t(64));
        int count = 0;
        std::string last;
        while (pull()) {
            if (pull->size() > 0) {
                ++count;
                last.assign(pull->data(), pull->size());
            }
        }
        ASSERT_TRUE(count == 4);
        ASSERT_TRUE(last == "2");
    }

    // ── 3. 动态链接链路：libc++_shared.so 应被动态加载 ──
    TEST("OHOS shared runtime loaded");
    int libcpp_loaded = 0;
    if (std::FILE *maps = std::fopen("/proc/self/maps", "r")) {
        char line[512];
        while (std::fgets(line, sizeof(line), maps)) {
            if (std::string_view(line).find("libc++_shared.so")
                    != std::string_view::npos) {
                libcpp_loaded = 1;
                break;
            }
        }
        std::fclose(maps);
    }
    ASSERT_TRUE(libcpp_loaded == 1);
    std::printf("[LINK] libc++_shared.so loaded = %d\n", libcpp_loaded);

    if (failures == 0) {
        std::printf("PASS: all HarmonyOS commata checks passed\n");
        return 0;
    }
    std::fprintf(stderr, "FAIL: %d HarmonyOS check(s) failed\n", failures);
    return 1;
}
