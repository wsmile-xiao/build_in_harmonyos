// Consumer test for taocpp-tuple 1.0.0 (header-only C++11 tuple library).
//
// 仅通过已安装的公开头文件 <tao/tuple/tuple.hpp> 使用 taocpp::tuple 的
// 公开 API：tao::tuple / tao::make_tuple / tao::tie / tao::tuple_cat /
// 按索引与按类型 get<> / 比较运算，验证第三方消费者可编译、链接并运行。
#include <tao/tuple/tuple.hpp>

#include <cassert>
#include <cstdio>
#include <string>
#include <type_traits>

int main()
{
    using namespace tao;

    // 构造 + 按索引 get
    auto t = tuple<int, double, std::string>(42, 3.14, std::string("hello"));
    static_assert(tuple_size<decltype(t)>::value == 3, "tuple size");
    assert(get<0>(t) == 42);
    assert(get<1>(t) == 3.14);
    assert(get<2>(t) == "hello");

    // 按类型 get
    assert(get<double>(t) == 3.14);
    assert(get<std::string>(t) == "hello");

    // make_tuple + 比较运算
    auto a = make_tuple(1, 2, 3);
    auto b = make_tuple(1, 2, 4);
    assert(a < b);
    assert(b > a);
    assert(a == a);
    assert(a != b);

    // tie 解包
    int x = 0;
    double y = 0.0;
    tie(x, y) = make_tuple(7, 2.5);
    assert(x == 7);
    assert(y == 2.5);

    // tuple_cat 拼接
    auto c = tuple_cat(make_tuple(1, true), make_tuple(), make_tuple(3UL, nullptr));
    static_assert(tuple_size<decltype(c)>::value == 4, "tuple_cat size");
    assert(get<0>(c) == 1);
    assert(get<1>(c) == true);
    assert(get<2>(c) == 3UL);
    assert(get<3>(c) == nullptr);

    std::puts("test_taocpp_tuple: taocpp::tuple public API consumed OK");
    return 0;
}
