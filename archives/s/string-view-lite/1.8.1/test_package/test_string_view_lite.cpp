// test_string_view_lite.cpp — L1 smoke test for string-view-lite 1.8.1 header-only library
// 验证 nonstd/string_view.hpp 头文件可正常包含、string_view 构造与访问
#include <nonstd/string_view.hpp>
#include <iostream>
#include <string>

int main() {
    // 测试 1: 从 C 字符串构造
    nonstd::string_view sv("hello");
    if (sv.size() != 5) {
        std::cerr << "FAIL: size should be 5" << std::endl;
        return 1;
    }

    // 测试 2: data() 和 operator[]
    if (sv[0] != 'h' || sv[4] != 'o') {
        std::cerr << "FAIL: character access failed" << std::endl;
        return 1;
    }

    // 测试 3: 从 std::string 构造
    std::string s = "world";
    nonstd::string_view sv2(s);
    if (sv2.length() != 5) {
        std::cerr << "FAIL: length from std::string should be 5" << std::endl;
        return 1;
    }

    // 测试 4: substr
    auto sub = sv.substr(1, 3);
    if (sub.size() != 3 || sub[0] != 'e') {
        std::cerr << "FAIL: substr should be 'ell'" << std::endl;
        return 1;
    }

    // 测试 5: compare
    if (sv.compare("hello") != 0) {
        std::cerr << "FAIL: compare should return 0" << std::endl;
        return 1;
    }

    // 测试 6: find
    if (sv.find("ll") != 2) {
        std::cerr << "FAIL: find 'll' should return 2" << std::endl;
        return 1;
    }

    // 测试 7: empty
    nonstd::string_view empty;
    if (!empty.empty()) {
        std::cerr << "FAIL: default constructed should be empty" << std::endl;
        return 1;
    }

    std::cout << "PASS: string-view-lite header-only 库链接和核心 API 验证通过" << std::endl;
    return 0;
}
