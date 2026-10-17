// test_expected_lite.cpp — L1 smoke test for expected-lite 0.6.3 header-only library
// 验证 nonstd/expected.hpp 头文件可正常包含、expected/unexpected 构造与访问
#include <nonstd/expected.hpp>
#include <iostream>
#include <string>

int main() {
    // 测试 1: 构造成功的 expected
    nonstd::expected<int, std::string> ok = 42;
    if (!ok.has_value() || ok.value() != 42) {
        std::cerr << "FAIL: expected value should be 42" << std::endl;
        return 1;
    }

    // 测试 2: 构造失败的 expected (unexpected)
    nonstd::expected<int, std::string> err = nonstd::make_unexpected(std::string("error"));
    if (err.has_value()) {
        std::cerr << "FAIL: unexpected should not have value" << std::endl;
        return 1;
    }
    if (err.error() != "error") {
        std::cerr << "FAIL: error message should be 'error'" << std::endl;
        return 1;
    }

    // 测试 3: operator* 访问值
    if (*ok != 42) {
        std::cerr << "FAIL: operator* should return 42" << std::endl;
        return 1;
    }

    // 测试 4: value_or 默认值
    nonstd::expected<int, int> e = nonstd::make_unexpected(1);
    if (e.value_or(99) != 99) {
        std::cerr << "FAIL: value_or should return 99" << std::endl;
        return 1;
    }

    // 测试 5: emplace 重新赋值
    ok.emplace(100);
    if (!ok.has_value() || ok.value() != 100) {
        std::cerr << "FAIL: emplace(100) should set value to 100" << std::endl;
        return 1;
    }

    // 测试 6: swap 交换 (成员函数)
    nonstd::expected<int, std::string> a = 1;
    nonstd::expected<int, std::string> b = 2;
    a.swap(b);
    if (a.value() != 2 || b.value() != 1) {
        std::cerr << "FAIL: swap should exchange values" << std::endl;
        return 1;
    }

    // 测试 7: operator bool 显式转换
    if (!static_cast<bool>(ok) || static_cast<bool>(err)) {
        std::cerr << "FAIL: operator bool conversion failed" << std::endl;
        return 1;
    }

    std::cout << "PASS: expected-lite header-only 库链接和核心 API 验证通过" << std::endl;
    return 0;
}
