// zug 0.1.2 消费者测试：只用已安装包的公开头文件 <zug/...> 做真实转导，
// 验证 compose / transducer / redutor / 变长输入 / 提前终止在 OHOS 上的行为。
#include <zug/compose.hpp>
#include <zug/into.hpp>
#include <zug/into_vector.hpp>
#include <zug/reduce.hpp>
#include <zug/reducing/last.hpp>
#include <zug/transduce.hpp>
#include <zug/transducer/count.hpp>
#include <zug/transducer/cycle.hpp>
#include <zug/transducer/filter.hpp>
#include <zug/transducer/map.hpp>
#include <zug/transducer/range.hpp>
#include <zug/transducer/take.hpp>
#include <zug/transducer/transducer.hpp>
#include <zug/util.hpp>

#include <functional>
#include <iostream>
#include <string>
#include <tuple>
#include <vector>

namespace {

int g_checks = 0;
int g_failed = 0;

void check(bool ok, const char *what)
{
    ++g_checks;
    if (!ok) {
        ++g_failed;
        std::cerr << "FAIL: " << what << std::endl;
    }
}

} // namespace

int main()
{
    using namespace zug;

    auto add_one   = [](int x) { return x + 1; };
    auto mult_five = [](int x) { return x * 5; };
    auto v         = std::vector<int>{1, 2, 3, 4};

    // compose：右到左组合 + operator|
    check(comp(add_one, mult_five)(10) == 51, "comp right-to-left");
    check(comp(mult_five, add_one)(10) == 55, "comp reversed order");
    auto inc = comp(add_one);
    check((inc | inc)(10) == 12, "operator| composition");

    // 直接转导到 vector
    check(into_vector(identity, v) == v, "into_vector identity");

    auto xform = comp(filter([](int x) { return x % 2 == 0; }),
                      map([](int x) { return std::to_string(x); }));
    check(into_vector(xform, v) == (std::vector<std::string>{"2", "4"}),
          "filter + map transduction");
    check(into(std::vector<std::string>{}, xform, v)
              == (std::vector<std::string>{"2", "4"}),
          "into appends into destination");

    // 类型擦除后的 transducer<In, Out> 管道
    auto erased = transducer<int, std::string>{xform};
    check(into_vector(erased, v) == (std::vector<std::string>{"2", "4"}),
          "type-erased transducer");

    // transduce：多输入变长、提前终止
    auto v1  = std::vector<int>{1, 2, 3, 6};
    auto v2  = std::vector<int>{1, 2, 1, 2};
    check(transduce(identity, std::plus<int>{}, 1, v1) == 13,
          "transduce identity fold");
    check(transduce(map(std::multiplies<int>{}), std::plus<int>{}, 1, v1, v2)
              == 21,
          "transduce variadic zip");
    auto four = {1, 2, 3, 4};
    check(transduce(take(2), std::plus<int>{}, 0, four) == 3,
          "transduce early termination");

    // reductor
    auto six = std::vector<int>{1, 2, 3, 6};
    check(reduce(last, 0, six) == 6, "reduce with last reductor");

    // 生成器型 transducer：range / count / cycle
    check(into_vector(range(2, 6, 2)) == (std::vector<int>{2, 4}),
          "range generator");
    check(into_vector(comp(count('a'), take(3)))
              == (std::vector<char>{'a', 'b', 'c'}),
          "count + take");
    check(into_vector(count(1.0, 0.5) | take(5))
              == (std::vector<double>{1.0, 1.5, 2.0, 2.5, 3.0}),
          "stepped count + take");
    auto cyc = std::vector<int>{0, 1};
    auto src = std::vector<int>{13, 42, 5};
    check(into_vector(cycle(cyc), src)
              == (std::vector<std::tuple<int, int>>{{13, 0}, {42, 1}, {5, 0}}),
          "cycle pairs source");

    // 变长 zip
    auto si = std::vector<int>{1, 2};
    auto ss = std::vector<std::string>{"a", "b"};
    check(into_vector(identity, si, ss)
              == (std::vector<std::tuple<int, std::string>>{{1, "a"}, {2, "b"}}),
          "variadic zip via identity");

    std::cout << "test_zug: " << (g_checks - g_failed) << "/" << g_checks
              << " assertions passed" << std::endl;
    return g_failed == 0 ? 0 : 1;
}
