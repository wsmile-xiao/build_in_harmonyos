// test_boolean_lite.cpp — L1 smoke test for boolean-lite 0.1.0 header-only library
// 验证 nonstd/boolean.hpp 可正常包含、boolean_ 构造/转换/比较/取反 API 可用
#include <nonstd/boolean.hpp>
#include <iostream>

int main() {
    using nonstd::boolean_;

    // 测试 1: 直接构造与 bool 转换
    boolean_ t(true);
    boolean_ f(false);
    if (!t) {
        std::cerr << "FAIL: boolean_(true) should be true" << std::endl;
        return 1;
    }
    if (f) {
        std::cerr << "FAIL: boolean_(false) should be false" << std::endl;
        return 1;
    }

    // 测试 2: 比较操作符
    if (!(t == boolean_(true))) {
        std::cerr << "FAIL: equality comparison" << std::endl;
        return 1;
    }
    if (!(t != f)) {
        std::cerr << "FAIL: inequality comparison" << std::endl;
        return 1;
    }
    if (!(f < t)) {
        std::cerr << "FAIL: ordering comparison" << std::endl;
        return 1;
    }

    // 测试 3: 取反
    boolean_ neg = !t;
    if (neg) {
        std::cerr << "FAIL: negation of true should be false" << std::endl;
        return 1;
    }

    std::cout << "PASS: boolean-lite header-only 库链接和核心 API 验证通过" << std::endl;
    return 0;
}