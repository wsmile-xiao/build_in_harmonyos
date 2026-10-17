// test_daw_header_libraries.cpp — L1 smoke test for daw-header-libraries 2.135.0 header-only library
// 验证 daw/daw_span.h / daw/daw_expected.h / daw/daw_string_view.h 头文件可正常包含与核心 API
#include <daw/daw_span.h>
#include <daw/daw_expected.h>
#include <daw/daw_string_view.h>
#include <iostream>
#include <string>
#include <vector>

int main() {
    // 测试 1: daw::span 构造与访问
    std::vector<int> v{1, 2, 3, 4, 5};
    daw::span<int> sp(v);
    if (sp.size() != 5) {
        std::cerr << "FAIL: span size should be 5" << std::endl;
        return 1;
    }
    if (sp[0] != 1 || sp[4] != 5) {
        std::cerr << "FAIL: span element access failed" << std::endl;
        return 1;
    }

    // 测试 2: daw::expected_t 基本用法（值路径）
    daw::expected_t<int> ok{ 42 };
    if (!ok.has_value() || *ok != 42) {
        std::cerr << "FAIL: expected_t value path failed" << std::endl;
        return 1;
    }

    // 测试 3: daw::expected_t 基本用法（异常/空路径）
    daw::expected_t<int> empty;
    if (empty.has_value()) {
        std::cerr << "FAIL: expected_t default should be empty" << std::endl;
        return 1;
    }

    // 测试 4: daw::string_view 构造与访问
    daw::string_view sv("hello");
    if (sv.size() != 5) {
        std::cerr << "FAIL: string_view size should be 5" << std::endl;
        return 1;
    }
    if (sv[0] != 'h' || sv[4] != 'o') {
        std::cerr << "FAIL: string_view character access failed" << std::endl;
        return 1;
    }

    std::cout << "PASS: daw-header-libraries header-only 库链接和核心 API 验证通过" << std::endl;
    return 0;
}