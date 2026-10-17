// HarmonyOS 专项测试 — cppcmd 0.1.0
//
// 本用例在 HarmonyOS OHOS arm64 运行时环境中编译并实际执行，验证 cppcmd
// 库（header-only C++ 命令解释器）在鸿蒙平台上的真实行为：
//  1. CommandInterpreter 命令注册与流式执行（std::stringstream 输入/输出）
//  2. Expression 表达式解析（command/args 拆分、空输入、空白修剪）
//  3. Value / as<T>() 类型转换（整数、布尔、字符串，含越界抛异常）
//
// 仅通过库公开头文件（cppcmd/CommandInterpreter.hpp 等）与公开 API 使用，
// 与上游 Catch2 测试、test_package 消费者测试相互独立，分别计数。

#include <iostream>
#include <sstream>
#include <string>
#include <vector>

#include <cppcmd/CommandInterpreter.hpp>
#include <cppcmd/Expression.hpp>
#include <cppcmd/Value.hpp>

using namespace cppcmd;
using namespace cppcmd::values;

static int failures = 0;

#define OHOS_CHECK(cond)                                                       \
    do {                                                                       \
        if (!(cond)) {                                                         \
            std::cerr << "OHOS_CHECK FAILED: " << #cond << " (line " << __LINE__ \
                      << ")" << std::endl;                                     \
            ++failures;                                                        \
        }                                                                      \
    } while (0)

int main() {
    // ── 1. CommandInterpreter：命令注册 + 流式执行（OHOS 运行时实际运行）──
    {
        std::stringstream input, output;
        CommandInterpreter interpreter(input, output);

        interpreter.registerCommand("sum", [](const auto& args, auto& os) {
            int total = 0;
            for (const auto& a : args) total += as<int>(a);
            os << total << std::endl;
        });

        input << "sum 10 20 30\n";
        interpreter.run();

        std::string line;
        std::getline(output, line);
        OHOS_CHECK(line == "60");
    }

    // ── 2. Expression 表达式解析 ──
    {
        Expression<std::string, std::vector<std::string>> exp{"cmd a1 a2"};
        OHOS_CHECK(static_cast<bool>(exp));
        OHOS_CHECK(exp.command() == "cmd");
        OHOS_CHECK(exp.args().size() == 2);
        OHOS_CHECK(exp.args()[0] == "a1");
        OHOS_CHECK(exp.args()[1] == "a2");

        Expression<std::string, std::vector<std::string>> empty{""};
        OHOS_CHECK(!static_cast<bool>(empty));
        OHOS_CHECK(empty.args().size() == 0);

        // 空白修剪（OHOS std::string / istringstream 行为验证）
        Expression<std::string, std::vector<std::string>> trim{"   cmd  x y "};
        OHOS_CHECK(trim.command() == "cmd");
        OHOS_CHECK(trim.args().size() == 2);
    }

    // ── 3. Value / as<T>() 类型转换 ──
    {
        OHOS_CHECK(as<int>("42") == 42);
        OHOS_CHECK(as<uint8_t>("0xff") == 255);
        OHOS_CHECK(as<int>("-0x0a") == -0x0a);
        OHOS_CHECK(as<bool>("true") == true);
        OHOS_CHECK(as<bool>("0") == false);

        bool threw = false;
        try {
            (void)as<uint8_t>("0xffff");  // 越界应抛 parse_error
        } catch (const parse_error&) {
            threw = true;
        }
        OHOS_CHECK(threw);
    }

    if (failures == 0) {
        std::cout << "OHOS special test cppcmd 0.1.0: ALL PASSED (3 suites)" << std::endl;
        return 0;
    }
    std::cerr << "OHOS special test cppcmd 0.1.0: FAILED (" << failures
              << " checks)" << std::endl;
    return 1;
}
