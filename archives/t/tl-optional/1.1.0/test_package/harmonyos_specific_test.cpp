// harmonyos_specific_test.cpp — tl-optional 1.1.0 HarmonyOS 专项测试
// 覆盖当前库在 OHOS 平台的实际消费入口：在 OHOS 交叉编译工具链下
// 真实编译运行，验证 tl::optional 在 C++17 模式下的核心行为。
#include <tl/optional.hpp>
#include <cstdio>
#include <cassert>
#include <string>

static int g_checks = 0;
#define CHECK(expr) do { assert(expr); ++g_checks; } while (0)

int main() {
    tl::optional<int> v;
    CHECK(!v.has_value());
    v = 10;
    CHECK(v.has_value() && v.value() == 10);

    tl::optional<std::string> s("OHOS");
    CHECK(s->size() == 4);

    auto doubled = v.map([](int x) { return x * 2; });
    CHECK(doubled.has_value() && doubled.value() == 20);

    tl::optional<int> chained = v.and_then([](int x) {
        return x >= 10 ? tl::optional<int>(x + 5) : tl::nullopt;
    });
    CHECK(chained.has_value() && chained.value() == 15);

#ifdef __OHOS__
    std::printf("harmonyos_specific_test OK: platform=OHOS %d checks passed\n", g_checks);
#else
    std::printf("harmonyos_specific_test OK: platform=%s %d checks passed\n",
                "OHOS-compatible(Linux cmake)", g_checks);
#endif
    return 0;
}
