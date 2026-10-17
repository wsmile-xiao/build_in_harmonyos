// arg_router 1.3.0 — test_package 消费者断言（鸿蒙特有测试行，R34/PF3/L0c）
//
// 通过 CMakeDeps 的 `arg_router::arg_router` 目标链接**打包后的头文件**（删掉包内
// include/ 任一件即断编译），真实调用 arg_router 的公开 API 解析 argv，全部在
// OHOS aarch64 + libc++ + C++17（上游默认配置：span-lite 提供 <nonstd/span.hpp>，
// 与上游 vcpkg.json / pr_checker.yml:155 同口径）的目标机上实编译实运行。
//
// 断言覆盖（6 条，与 test_package/MANIFEST.yml 的 consumer_checks 一一对应）：
//   1. 长选项取值解析（--name hello → router 收到 "hello"）
//   2. 短选项解析（-v → verbose=true）
//   3. 默认值回落（未给 --count → 1）
//   4. 非 ASCII（UTF-8）取值往返（--name 鸿蒙PC → 字节级相等，覆盖 OHOS 无
//      传统 locale、依赖 UTF-8 字面宽度处理的路径）
//   5. 非法 int 取值走异常路径（--count abc → 抛 std::exception 且 router 未被调用）
//
// 末行输出 `ARG-ROUTER-CONSUMER checks=<N> failures=<M>`，MANIFEST.yml 与 PR 正文的
// 「鸿蒙特有测试」行以该行数字为准。

#include <arg_router/arg_router.hpp>

#include <iostream>
#include <string>
#include <string_view>
#include <vector>

namespace ar = arg_router;
namespace arp = ar::policy;

namespace
{
int g_checks = 0;
int g_failures = 0;

void check(const bool ok, const std::string_view& what)
{
    ++g_checks;
    if (ok) {
        std::cout << "[ok]   " << what << std::endl;
    } else {
        ++g_failures;
        std::cerr << "[fail] " << what << std::endl;
    }
}

struct parse_result {
    bool router_hit = false;
    bool verbose = false;
    int count = 0;
    std::string name;
};

// 同一棵 parse 树复用（tree_node::parse 可重复调用，与上游 test/root_tests 同型）
parse_result g_result{};
bool g_hit = false;
}  // namespace

int main()
{
    const auto r = ar::root(
        ar::mode(ar::flag(arp::long_name<AR_STRING("verbose")>,
                          arp::short_name<'v'>,
                          arp::description<AR_STRING("Verbose output")>),
                 ar::arg<int>(arp::long_name<AR_STRING("count")>,
                              arp::default_value(1),
                              arp::description<AR_STRING("How many times")>),
                 ar::arg<std::string>(arp::long_name<AR_STRING("name")>,
                                      arp::default_value(std::string{}),
                                      arp::description<AR_STRING("Target name (UTF-8)")>),
                 arp::router{[](const bool verbose, const int count, const std::string& name) {
                     g_result = parse_result{true, verbose, count, name};
                     g_hit = true;
                 }}),
        arp::validation::default_validator);

    // argv 需要可写 char*（与上游 test/root_tests 的 const_cast<char**> 同型，此处直接给
    // 非 const 缓冲，免去 const_cast）
    auto parse_ok = [&](std::vector<std::string> args) {
        std::vector<char*> argv;
        argv.reserve(args.size());
        for (auto& s : args) {
            argv.push_back(s.data());
        }
        g_hit = false;
        g_result = parse_result{};
        r.parse(static_cast<int>(argv.size()), argv.data());
        return g_hit;
    };

    // 1) 长选项取值解析
    check(parse_ok({"arg_router_consumer", "--name", "hello"}) && g_result.name == "hello",
          "long-option value parsed (--name hello)");

    // 2) 短选项解析
    check(parse_ok({"arg_router_consumer", "-v"}) && g_result.verbose,
          "short-option flag parsed (-v)");

    // 3) 默认值回落
    check(parse_ok({"arg_router_consumer", "--count", "0"}) && g_result.count == 0,
          "explicit value parsed (--count 0)");
    check(parse_ok({"arg_router_consumer"}) && g_result.count == 1,
          "default value applied when option omitted (count==1)");

    // 4) 非 ASCII（UTF-8）取值往返
    const auto utf8_name = std::string{"\xe9\xb8\xbf\xe8\x92\x99PC"};  // 鸿蒙PC
    check(parse_ok({"arg_router_consumer", "--name", utf8_name}) && g_result.name == utf8_name,
          "non-ASCII (UTF-8) value round-trip (鸿蒙PC)");

    // 5) 非法 int 取值走异常路径（router 必须没被调用）
    auto threw = false;
    try {
        parse_ok({"arg_router_consumer", "--count", "abc"});
    } catch (const std::exception&) {
        threw = true;
    }
    check(threw && !g_hit, "invalid int value throws and router not invoked");

    std::cout << "ARG-ROUTER-CONSUMER checks=" << g_checks << " failures=" << g_failures
              << std::endl;
    return g_failures == 0 ? 0 : 1;
}
