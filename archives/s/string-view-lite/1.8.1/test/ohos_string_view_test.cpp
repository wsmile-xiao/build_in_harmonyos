// ohos_string_view_test.cpp — HarmonyOS 专项测试（string-view-lite 1.8.1）
//
// 目的：验证 string-view-lite 头文件在 HarmonyOS aarch64 (musl) 环境下的真实
// 消费入口可编译、可链接、可运行。以 clang (OHOS 工具链) 编译为 aarch64
// 可执行文件，并在本机 (OHOS) 直接运行。覆盖 header-only 库实际调用路径：
// 构造 / 访问 / substr / find / std::string 互转，并额外验证在 OHOS 下
// string_view 与 C 风格接口 (printf) 混用无 ABI/内存问题。
#include <nonstd/string_view.hpp>
#include <cstdio>
#include <cstring>
#include <string>

static int failures = 0;

#define CHECK(cond)                                                     \
    do {                                                                \
        if (!(cond)) {                                                  \
            std::printf("FAIL: %s (line %d)\n", #cond, __LINE__);       \
            ++failures;                                                 \
        }                                                               \
    } while (0)

int main() {
    // 1) C 字符串构造 + size/data
    const char* txt = "HarmonyOS string-view-lite test";
    nonstd::string_view sv(txt);
    CHECK(sv.size() == std::strlen(txt));
    CHECK(sv.data() == txt);

    // 2) 字符访问
    CHECK(sv[0] == 'H');
    CHECK(sv.back() == 't');

    // 3) substr
    nonstd::string_view sub = sv.substr(0, 9);
    CHECK(sub.size() == 9);
    CHECK(std::memcmp(sub.data(), "HarmonyOS", 9) == 0);

    // 4) find
    CHECK(sv.find("string-view") == 10);
    CHECK(sv.find("nope") == nonstd::string_view::npos);

    // 5) compare
    CHECK(sv.compare(nonstd::string_view(txt)) == 0);
    CHECK(sv.compare(nonstd::string_view("xxx")) != 0);

    // 6) std::string 互转
    std::string st(txt);
    nonstd::string_view sv2(st.data(), st.size());
    CHECK(sv2 == sv);

    // 7) 与 C 风格接口混用（OHOS 下常见场景：日志/printf 打印视图内容）
    nonstd::string_view head = sv.substr(0, 9);
    std::printf("OHOS 专项测试打印: [%.*s] size=%zu\n",
                static_cast<int>(head.size()), head.data(), sv.size());

    if (failures == 0) {
        std::printf("PASS: string-view-lite 1.8.1 HarmonyOS 专项测试全部通过\n");
        return 0;
    }
    std::printf("FAIL: %d 项检查未通过\n", failures);
    return 1;
}
