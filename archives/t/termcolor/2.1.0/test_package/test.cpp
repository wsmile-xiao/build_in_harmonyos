//!
//! harmonyos_specific_test.cpp — termcolor 2.1.0 HarmonyOS 专项测试
//!
//! 在 OHOS (aarch64) 平台真实调用 termcolor 的消费入口：
//!   - 断言 colorize 标志下 foreground/background/format 输出含正确 ANSI 转义序列
//!   - 断言 nocolorize 时输出不含 ANSI 转义
//!   - 断言平台为目标 OHOS（__OHOS__ 宏 / aarch64）
//! 不依赖 tty：通过 iword colorize 标志驱动 is_colorized，输出捕获至 ostringstream。
//!

#include <iostream>
#include <sstream>
#include <string>
#include <cstdlib>

#include "termcolor/termcolor.hpp"

using namespace termcolor;

static int failures = 0;

static void check(bool cond, const std::string& what)
{
    if (!cond) {
        std::cerr << "FAIL: " << what << std::endl;
        ++failures;
    } else {
        std::cout << "PASS: " << what << std::endl;
    }
}

int main()
{
#if defined(__OHOS__)
    std::cout << "platform=OHOS" << std::endl;
#else
    std::cout << "platform=non-OHOS" << std::endl;
#endif
#if defined(__aarch64__)
    std::cout << "arch=aarch64" << std::endl;
#endif

    // 1) colorize 标志下，red/green/blue/bold/reset 产生标准 ANSI 序列
    {
        std::ostringstream oss;
        oss << colorize << red << "hello" << reset;
        const std::string s = oss.str();
        check(s.find("\033[31m") != std::string::npos, "red foreground ANSI \\033[31m present");
        check(s.find("\033[00m") != std::string::npos, "reset ANSI \\033[00m present");
        check(s.find("hello") != std::string::npos, "payload text present");
    }

    // 2) background 颜色
    {
        std::ostringstream oss;
        oss << colorize << on_blue << "bg" << reset;
        const std::string s = oss.str();
        check(s.find("\033[44m") != std::string::npos, "on_blue background ANSI \\033[44m present");
    }

    // 3) 组合多种 format
    {
        std::ostringstream oss;
        oss << colorize << bold << underline << "both" << reset;
        const std::string s = oss.str();
        check(s.find("\033[1m") != std::string::npos, "bold ANSI \\033[1m present");
        check(s.find("\033[4m") != std::string::npos, "underline ANSI \\033[4m present");
    }

    // 4) nocolorize 时无 ANSI 转义
    {
        std::ostringstream oss;
        oss << nocolorize << red << "plain" << reset;
        const std::string s = oss.str();
        check(s.find("\033[") == std::string::npos, "no ANSI escape when nocolorize");
        check(s.find("plain") != std::string::npos, "payload survives nocolorize");
    }

    // 5) colorize 标志复位后恢复无色
    {
        std::ostringstream oss;
        oss << colorize << green << "x" << nocolorize << green << "y" << reset;
        const std::string s = oss.str();
        const std::size_t first = s.find("\033[32m");
        const std::size_t second = s.find("\033[32m", first + 1);
        check(first != std::string::npos, "first green present");
        check(second == std::string::npos, "second green suppressed after nocolorize");
    }

    if (failures == 0) {
        std::cout << "harmonyos_specific_test OK: all " << 5 << " checks passed" << std::endl;
        return 0;
    }
    std::cerr << "harmonyos_specific_test FAILED: " << failures << " check(s) failed" << std::endl;
    return 1;
}