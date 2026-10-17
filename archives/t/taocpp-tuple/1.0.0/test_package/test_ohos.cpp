// taocpp-tuple 1.0.0 HarmonyOS 专项测试（OHOS 工具链真实运行，独立于上游用例）。
//
// 目的：在 OHOS（aarch64-unknown-linux-ohos clang 15, libc++17）交叉工具链下，
// 验证 taocpp::tuple 公开头文件 <tao/tuple/tuple.hpp> 实例化后的真实可观察
// 结果：constexpr 编译期计算、按索引/按类型 get<>、比较运算、tie 解包、
// tuple_cat 拼接、默认构造与复制。全部断言在 OHOS 设备侧进程内执行，
// 非仅编译不运行的空壳。
#include <tao/tuple/tuple.hpp>

#include <cassert>
#include <cstdio>
#include <string>
#include <type_traits>

int main()
{
    using namespace tao;

    // 默认构造（空元素值初始化）
    auto def = tuple<int, double, int>();
    assert(get<0>(def) == 0);
    assert(get<1>(def) == 0.0);
    assert(get<2>(def) == 0);

    // constexpr 编译期计算（OHOS clang 15 支持 C++14 扩展 constexpr）
    constexpr auto ce = make_tuple(1, 2, 3);
    static_assert(tuple_size<decltype(ce)>::value == 3, "constexpr size");
    static_assert(get<0>(ce) == 1 && get<2>(ce) == 3, "constexpr get");
    static_assert(ce == make_tuple(1, 2, 3), "constexpr eq");

    // 按类型 get（唯一类型元素）
    auto mixed = tuple<int, double, std::string>(7, 0.5, std::string("ohos"));
    assert(get<int>(mixed) == 7);
    assert(get<double>(mixed) == 0.5);
    assert(get<std::string>(mixed) == "ohos");

    // tie 解包赋值（显式 tao:: 前缀，避免与 libc++ <string> 引入的
    // std::tie/std::make_tuple 泛型模板重载歧义）
    int a = 0, b = 0;
    std::string s;
    tao::tie(a, b, s) = tao::make_tuple(11, 22, std::string("tuple"));
    assert(a == 11);
    assert(b == 22);
    assert(s == "tuple");

    // tuple_cat 拼接
    auto cat = tuple_cat(make_tuple(1), make_tuple(2.5, true), make_tuple());
    static_assert(tuple_size<decltype(cat)>::value == 3, "cat size");
    assert(get<0>(cat) == 1);
    assert(get<1>(cat) == 2.5);
    assert(get<2>(cat) == true);

    // 复制构造与比较运算
    auto src = make_tuple(1, 2, 3);
    auto cpy(src);
    assert(cpy == src);
    assert(cpy >= src && cpy <= src);
    assert(src < make_tuple(1, 2, 4));
    assert(src > make_tuple(1, 2, 2));
    assert(src != make_tuple(1, 2, 2));

    // 空 tuple
    assert(tuple<>() == tuple<>());
    assert(!(tuple<>() < tuple<>()));

    std::puts("taocpp-tuple 1.0.0 OHOS 专项测试: PASS (constexpr/get/tie/cat/cmp 全通过)");
    return 0;
}
