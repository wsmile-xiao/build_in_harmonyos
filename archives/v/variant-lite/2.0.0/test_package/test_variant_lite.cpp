// test_variant_lite.cpp — L1 smoke test for variant-lite 2.0.0 header-only library
// 验证 nonstd/variant.hpp 头文件可正常包含、variant 构造与访问
// Force the nonstd implementation to avoid std::variant overload-resolution
// differences on OHOS clang 15 libc++ (see conanfile.py VARIANT_LITE_OPT_SELECT_NONSTD).
#include <nonstd/variant.hpp>
#include <iostream>
#include <string>

int main() {
    // 测试 1: 构造 variant 并存储 int
    nonstd::variant<int, double, std::string> v = 42;
    if (nonstd::get<int>(v) != 42) {
        std::cerr << "FAIL: get<int> should return 42" << std::endl;
        return 1;
    }

    // 测试 2: index()
    if (v.index() != 0) {
        std::cerr << "FAIL: index should be 0 for int" << std::endl;
        return 1;
    }

    // 测试 3: 赋值为 string
    v = std::string("hello");
    if (nonstd::get<std::string>(v) != "hello") {
        std::cerr << "FAIL: get<string> should return 'hello'" << std::endl;
        return 1;
    }
    if (v.index() != 2) {
        std::cerr << "FAIL: index should be 2 for string" << std::endl;
        return 1;
    }

    // 测试 4: holds_alternative
    if (!nonstd::holds_alternative<std::string>(v)) {
        std::cerr << "FAIL: should hold string alternative" << std::endl;
        return 1;
    }

    // 测试 5: get_if
    auto* ptr = nonstd::get_if<double>(&v);
    if (ptr != nullptr) {
        std::cerr << "FAIL: get_if<double> should return nullptr" << std::endl;
        return 1;
    }

    // 测试 6: visit
    struct Visitor {
        int operator()(int i) const { return i; }
        int operator()(double d) const { return (int)d; }
        int operator()(const std::string& s) const { return (int)s.size(); }
    };
    int result = nonstd::visit(Visitor(), v);
    if (result != 5) {
        std::cerr << "FAIL: visit should return 5 (string length)" << std::endl;
        return 1;
    }

    // 测试 7: 赋值为 double
    v = 3.14;
    if (nonstd::get<double>(v) < 3.13 || nonstd::get<double>(v) > 3.15) {
        std::cerr << "FAIL: get<double> should return ~3.14" << std::endl;
        return 1;
    }

    std::cout << "PASS: variant-lite header-only 库链接和核心 API 验证通过" << std::endl;
    return 0;
}
