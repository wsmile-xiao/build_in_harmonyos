// ohos_scope_test.cpp — HarmonyOS 专项测试（scope-lite 0.3.0）
//
// 目的：验证 scope-lite 头文件在 HarmonyOS aarch64 (musl) 环境下的真实
// 消费入口可编译、可链接、可运行。以 clang 15 (OHOS 工具链) 编译为 aarch64
// 可执行文件，并在本机 (OHOS) 直接运行。覆盖 header-only 库实际调用路径：
// scope_exit / scope_fail / scope_success 语义，并额外验证在 OHOS 下
// scope guard 与 C 风格接口 (printf) 混用无 ABI/内存问题。
#include <nonstd/scope.hpp>
#include <cstdio>
#include <cstdlib>

static int failures = 0;

#define CHECK(cond)                                                     \
    do {                                                                \
        if (!(cond)) {                                                  \
            std::printf("FAIL: %s (line %d)\n", #cond, __LINE__);       \
            ++failures;                                                 \
        }                                                               \
    } while (0)

int main() {
    using nonstd::make_scope_exit;
    using nonstd::make_scope_fail;
    using nonstd::make_scope_success;

    // 1) scope_exit 作用域退出执行
    int exits = 0;
    {
        auto guard = make_scope_exit([&exits]() { ++exits; });
        CHECK(exits == 0);
    }
    CHECK(exits == 1);

    // 2) scope_fail 正常退出不执行
    int fails = 0;
    {
        auto guard = make_scope_fail([&fails]() { ++fails; });
    }
    CHECK(fails == 0);

    // 3) scope_success 正常退出执行
    int successes = 0;
    {
        auto guard = make_scope_success([&successes]() { ++successes; });
    }
    CHECK(successes == 1);

    // 4) 与 C 风格接口混用（OHOS 下常见场景：日志/printf）
    int counted = 0;
    {
        auto guard = make_scope_exit([&counted]() {
            std::printf("OHOS scope guard 退出钩子执行, counted=%d\n", counted + 1);
            ++counted;
        });
        std::printf("OHOS 专项测试: scope guard 活动\n");
    }
    CHECK(counted == 1);

    if (failures == 0) {
        std::printf("PASS: scope-lite 0.3.0 HarmonyOS 专项测试全部通过\n");
        return 0;
    }
    std::printf("FAILED: %d 项失败\n", failures);
    return 1;
}