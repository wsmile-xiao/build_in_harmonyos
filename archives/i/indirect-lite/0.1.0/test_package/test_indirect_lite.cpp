// test_indirect_lite.cpp — L1 smoke test for indirect-lite 0.1.0 header-only library
// 验证 nonstd/indirect_value.hpp 头文件可正常包含、indirect_value 构造与访问
#include <nonstd/indirect_value.hpp>
#include <iostream>
#include <string>
#include <utility>

using nonstd::indirect_value;

int main() {
    // 测试 1: 从裸指针构造（获得所有权）
    indirect_value<int> p(new int(42));
    if (!p || *p != 42) {
        std::cerr << "FAIL: indirect_value from pointer should hold 42" << std::endl;
        return 1;
    }

    // 测试 2: operator-> 访问成员
    int * raw = p.operator->();
    if (raw == nullptr || *raw != 42) {
        std::cerr << "FAIL: operator-> should return the held pointer" << std::endl;
        return 1;
    }

    // 测试 3: 构造空 indirect_value（默认构造）
    indirect_value<int> empty;
    if (empty) {
        std::cerr << "FAIL: default constructed indirect_value should be empty" << std::endl;
        return 1;
    }

    // 测试 4: in_place 构造（不移动、不复制构造参数）
    indirect_value<std::string> s(nonstd::in_place, "hello");
    if (!s || *s != "hello") {
        std::cerr << "FAIL: in_place constructed indirect_value should hold 'hello'" << std::endl;
        return 1;
    }

    // 测试 5: 移动构造接管指针（原对象变空）
    indirect_value<int> src(new int(7));
    indirect_value<int> dst(std::move(src));
    if (!dst || *dst != 7 || src) {
        std::cerr << "FAIL: move construction should transfer ownership" << std::endl;
        return 1;
    }

    // 测试 6: swap 交换
    indirect_value<int> a(new int(1));
    indirect_value<int> b(new int(2));
    a.swap(b);
    if (*a != 2 || *b != 1) {
        std::cerr << "FAIL: swap should exchange held values" << std::endl;
        return 1;
    }

    // 测试 7: value()/has_value() 访问（扩展 API）
    if (!p.has_value() || p.value() != 42 || !s.has_value() || s.value() != "hello") {
        std::cerr << "FAIL: value()/has_value() should reflect engaged state" << std::endl;
        return 1;
    }

    std::cout << "PASS: indirect-lite header-only 库链接和核心 API 验证通过" << std::endl;
    return 0;
}