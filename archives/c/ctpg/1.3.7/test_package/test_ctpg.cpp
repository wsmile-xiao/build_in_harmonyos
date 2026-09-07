// test_ctpg.cpp — ctpg 1.3.7 消费者验证（R34: 真实调用被测包 API）
//
// 使用 CTPG 编译期解析器生成器定义一个表达式解析器（数字列表求和），
// 编译期与运行期各解析一次，断言结果，验证头文件在目标平台实际可用。
#include <ctpg/ctpg.hpp>
#include <cassert>
#include <iostream>
#include <string_view>

using namespace ctpg;
using namespace ctpg::buffers;

constexpr nterm<int> list("list");

constexpr char number_pattern[] = "[1-9][0-9]*";
constexpr regex_term<number_pattern> number("number");

constexpr int to_int(std::string_view sv)
{
    int sum = 0;
    for (auto c : sv) { sum *= 10; sum += c - '0'; }
    return sum;
}

constexpr parser p(
    list,
    terms(',', number),
    nterms(list),
    rules(
        list(number) >= to_int,
        list(list, ',', number)
            >= [](int sum, char, const auto& n) { return sum + to_int(n); }
    )
);

int main()
{
    // 运行期解析
    auto res = p.parse(cstring_buffer("1, 2, 3"));
    assert(res.has_value());
    assert(res.value() == 6);

    // 编译期解析（CTPG 核心能力）
    constexpr char example_text[] = "4, 5";
    constexpr auto cres = p.parse(cstring_buffer(example_text));
    static_assert(cres.has_value(), "compile-time parse must succeed");
    static_assert(cres.value() == 9, "compile-time parse value");

    std::cout << "ctpg 1.3.7 consumer test OK: 1+2+3=6, 4+5=9" << std::endl;
    return 0;
}
