// test_optional_lite.cpp — L1 smoke test for optional-lite 3.5.0 header-only library
// 验证 nonstd/optional.hpp 头文件可正常包含、optional 构造与访问
#include <nonstd/optional.hpp>
#include <iostream>
#include <string>

int main() {
    // 测试 1: 空 optional
    nonstd::optional<int> empty;
    if (empty.has_value()) {
        std::cerr << "FAIL: empty optional should not have value" << std::endl;
        return 1;
    }

    // 测试 2: 有值的 optional
    nonstd::optional<int> opt = 42;
    if (!opt.has_value() || *opt != 42) {
        std::cerr << "FAIL: optional value should be 42" << std::endl;
        return 1;
    }

    // 测试 3: value() 访问
    if (opt.value() != 42) {
        std::cerr << "FAIL: value() should return 42" << std::endl;
        return 1;
    }

    // 测试 4: value_or 默认值
    if (empty.value_or(99) != 99) {
        std::cerr << "FAIL: value_or should return 99" << std::endl;
        return 1;
    }

    // 测试 5: make_optional
    auto opt2 = nonstd::make_optional(std::string("hello"));
    if (!opt2.has_value() || opt2->size() != 5) {
        std::cerr << "FAIL: make_optional string should have length 5" << std::endl;
        return 1;
    }

    // 测试 6: 重新赋值
    opt = 100;
    if (*opt != 100) {
        std::cerr << "FAIL: reassigned value should be 100" << std::endl;
        return 1;
    }

    // 测试 7: reset
    opt.reset();
    if (opt.has_value()) {
        std::cerr << "FAIL: reset should clear value" << std::endl;
        return 1;
    }

    std::cout << "PASS: optional-lite header-only 库链接和核心 API 验证通过" << std::endl;
    return 0;
}
