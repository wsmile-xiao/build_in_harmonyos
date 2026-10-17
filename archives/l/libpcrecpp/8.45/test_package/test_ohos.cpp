// HarmonyOS 专项测试 — libpcrecpp 8.45
//
// 本测试是鸿蒙平台专项用例，验证 OHOS 适配后 libpcrecpp 库的行为：
// 1) 编译目标确为 HarmonyOS（__OHOS__ 宏存在）
// 2) pcrecpp::RE 在 OHOS 上完整工作（compile/fullmatch/partialmatch）
// 3) pcrecpp::StringPiece 正常工作（无后端/无异常崩溃）
// 4) 动态链接/静态库符号解析在 OHOS 上正常（API 调用即证明）
#include <pcrecpp.h>
#include <pcre_stringpiece.h>
#include <cstdio>
#include <cstring>
#include <string>

// 平台断言：OHOS 编译环境下必须定义 __OHOS__
#ifdef __OHOS__
#define OHOS_PLATFORM_VERIFIED 1
#else
#define OHOS_PLATFORM_VERIFIED 0
#endif

static int failures = 0;

#define CHECK(cond, msg) do { \
    if (!(cond)) { \
        std::fprintf(stderr, "[FAIL] %s @%d\n", msg, __LINE__); \
        failures++; \
    } else { \
        std::fprintf(stdout, "[PASS] %s\n", msg); \
    } \
} while (0)

int main() {
    // 1) 平台验证：确认编译目标为 HarmonyOS
    CHECK(OHOS_PLATFORM_VERIFIED, "OHOS 平台宏验证 (__OHOS__ defined)");

    // 2) 库版本宏：验证 pcrecpp 头文件与 pcre 主库版本声明一致（8.45）
    CHECK(PCRE_MAJOR == 8 && PCRE_MINOR == 45,
          "PCRE 版本宏 (PCRE_MAJOR=8, PCRE_MINOR=45)");
    std::fprintf(stdout, "  PCRE version: %d.%d\n", PCRE_MAJOR, PCRE_MINOR);

    // 3) 核心 API 验证：pcrecpp::RE FullMatch + 捕获组（OHOS 上符号解析正常）
    pcrecpp::RE re("(\\d+)-(\\d+)");
    std::string left, right;
    CHECK(re.FullMatch("123-456", &left, &right),
          "pcrecpp::RE::FullMatch 调用成功（动态符号解析正常）");
    CHECK(left == "123" && right == "456",
          "pcrecpp::RE FullMatch 捕获组结果正确");

    // 4) PartialMatch + error() 路径
    pcrecpp::RE re2("world");
    CHECK(re2.PartialMatch("hello world"), "pcrecpp::RE::PartialMatch 调用成功");
    pcrecpp::RE bad("[unclosed");
    CHECK(bad.error().empty() == false, "非法模式 error() 返回非空（错误路径正常）");

    // 5) StringPiece 消费验证（无崩溃）
    pcrecpp::StringPiece sp("a=1&b=2");
    pcrecpp::RE re3("b=(\\d+)");
    int bval = 0;
    CHECK(re3.FindAndConsume(&sp, &bval) && bval == 2,
          "pcrecpp::StringPiece FindAndConsume 调用成功");

    // 6) 大小写不敏感选项（RE_Options 路径）
    pcrecpp::RE re4("hello", pcrecpp::RE_Options().set_caseless(true));
    CHECK(re4.FullMatch("HELLO"), "pcrecpp::RE_Options caseless 匹配正常");

    if (failures == 0) {
        std::fprintf(stdout, "test_ohos: ALL PASS (%d checks)\n", 6);
        return 0;
    }
    std::fprintf(stderr, "test_ohos: %d FAILURES\n", failures);
    return 1;
}
