// etl 20.38.4 test_package — 消费方视角 L1 测试
// 验证 header-only etl 的头文件在编译期 (constexpr) 与运行期均可使用。
#include <cassert>
#include <iostream>
#include <string>

#include "etl/array.h"
#include "etl/optional.h"
#include "etl/string.h"
#include "etl/vector.h"

// 编译期常量表达式断言（etl::array / etl::optional）
static_assert(etl::array<int, 3>{1, 2, 3}.size() == 3, "etl::array size failed");
static_assert(!etl::optional<int>{}.has_value(), "etl::optional default empty");

int main() {
    // etl::vector 运行期使用
    etl::vector<int, 8> v;
    v.push_back(1);
    v.push_back(2);
    v.push_back(3);
    assert(v.size() == 3);
    assert(v[0] == 1 && v[2] == 3);

    // etl::optional 运行期使用
    etl::optional<int> opt(42);
    assert(opt.has_value());
    assert(*opt == 42);
    etl::optional<int> empty;
    assert(!empty.has_value());

    // etl::string 运行期使用
    etl::string<16> s("hello");
    s += " etl";
    assert(s == "hello etl");

    std::cout << "etl test_package OK: static/compile-time and runtime checks passed"
              << std::endl;
    return 0;
}