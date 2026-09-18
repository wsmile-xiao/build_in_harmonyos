// test_any_lite.cpp — L1 smoke test for any-lite 0.3.0.1 header-only library
// 验证 nonstd/any.hpp 头文件可正常包含、any 构造与 any_cast 访问
#include <nonstd/any.hpp>
#include <iostream>
#include <string>

int main() {
    // 测试 1: int 值
    nonstd::any a = 42;
    if (nonstd::any_cast<int>(a) != 42) {
        std::cerr << "FAIL: any_cast<int> should return 42" << std::endl;
        return 1;
    }

    // 测试 2: std::string 值
    a = std::string("hello");
    if (nonstd::any_cast<std::string>(a) != "hello") {
        std::cerr << "FAIL: any_cast<string> should return hello" << std::endl;
        return 1;
    }

    // 测试 3: has_value
    nonstd::any empty;
    if (empty.has_value()) {
        std::cerr << "FAIL: default-constructed any should be empty" << std::endl;
        return 1;
    }
    if (!a.has_value()) {
        std::cerr << "FAIL: assigned any should have value" << std::endl;
        return 1;
    }

    std::cout << "PASS: any-lite header-only 库链接和核心 API 验证通过" << std::endl;
    return 0;
}
