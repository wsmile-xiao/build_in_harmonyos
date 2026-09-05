// test_scope_lite.cpp — L1 smoke test for scope-lite 0.3.0 header-only library
// 验证 nonstd/scope.hpp 头文件可正常包含、scope_exit/scope_fail/scope_success 语义
#include <nonstd/scope.hpp>

#include <iostream>
#include <string>

int main() {
    using nonstd::make_scope_exit;
    using nonstd::make_scope_fail;
    using nonstd::make_scope_success;

    // 测试 1: make_scope_exit 在作用域退出时执行
    int exited = 0;
    {
        auto guard = make_scope_exit([&exited]() { ++exited; });
        if (exited != 0) {
            std::cerr << "FAIL: scope_exit should not run yet" << std::endl;
            return 1;
        }
    }
    if (exited != 1) {
        std::cerr << "FAIL: scope_exit should have run once at scope exit" << std::endl;
        return 1;
    }

    // 测试 2: make_scope_fail 仅在异常路径退出时执行
    int failed = 0;
    {
        auto guard = make_scope_fail([&failed]() { ++failed; });
    }
    if (failed != 0) {
        std::cerr << "FAIL: scope_fail should not run on normal exit" << std::endl;
        return 1;
    }

    // 测试 3: make_scope_success 仅在正常路径退出时执行
    int succeeded = 0;
    {
        auto guard = make_scope_success([&succeeded]() { ++succeeded; });
    }
    if (succeeded != 1) {
        std::cerr << "FAIL: scope_success should run once on normal exit" << std::endl;
        return 1;
    }

    // 测试 4: 返回函数值时 scope_exit 仍然生效
    int counted = 0;
    auto helper = [&counted]() -> int {
        auto guard = make_scope_exit([&counted]() { ++counted; });
        return 42;
    };
    if (helper() != 42) {
        std::cerr << "FAIL: helper should return 42" << std::endl;
        return 1;
    }
    if (counted != 1) {
        std::cerr << "FAIL: scope_exit should run before function returns" << std::endl;
        return 1;
    }

    std::cout << "PASS: scope-lite header-only 库链接和核心 API 验证通过" << std::endl;
    return 0;
}
