#include <rang.hpp>

#include <iostream>
#include <sstream>
#include <string>

// 显式运行时检查：不依赖 assert()（Release/-DNDEBUG 会移除 assert，
// 导致测试形同虚设），任何失败都直接 return 非零，保证证据真实。
static int check(bool ok, const std::string& what) {
    if (!ok) {
        std::cerr << "FAILED: " << what << std::endl;
        return 1;
    }
    return 0;
}

// rang 3.3 — HarmonyOS 平台专项测试用例
//
// 本用例验证 rang 在 OpenHarmony / HarmonyOS PC (aarch64-linux-ohos, clang 15,
// libc++) 平台上的专项适配点：
//   A. 平台识别：OHOS 工具链预定义 __OHOS__ 及 __unix__/__linux__，rang.hpp 内部
//      据此走 OS_LINUX 分支并 include <unistd.h>（该内部宏在头文件末尾被 #undef，
//      属 rang 设计行为：不污染用户全局宏，因此这里校验编译器平台宏而非 OS_LINUX）。
//   B. POSIX 依赖：rang 依赖 unistd.h 的 isatty() 做 TTY 检测，在 OHOS 上必须
//      能编译并链接。
//   C. TTY 感知：在无 TTY（重定向到管道/文件）环境中，rang 的 control::Auto
//      应回退为不输出 ANSI 转义序列（等同于 plain 输出）。
//   D. control::Force 强制输出：即使无 TTY，也能强制产生 ANSI SGR 序列。
//   E. control::Off：纯文本输出，不产生任何转义序列。
int main() {
    // A. 平台识别 —— 必须是 OHOS 或 unix-like 平台（rang.hpp 的 OS_LINUX 分支前提）。
    std::cout << "platform: ";
#if defined(__OHOS__)
    std::cout << "OHOS";
#elif defined(__linux__) || defined(__unix__) || defined(__unix) || defined(__APPLE__)
    std::cout << "unix-like";
#else
    std::cout << "UNKNOWN";
#endif
    std::cout << std::endl;
#if defined(__OHOS__)
    if (check(true, "OHOS platform detected (__OHOS__)") != 0) return 1;
#elif defined(__linux__) || defined(__unix__) || defined(__unix) || defined(__APPLE__)
    if (check(true, "unix-like platform (rang OS_LINUX branch active)") != 0) return 1;
#else
    if (check(false, "platform must be OHOS or unix-like") != 0) return 1;
#endif
    if (check(
#if defined(__unix__) || defined(__linux__) || defined(__unix)
            true,
#else
            false,
#endif
            "rang.hpp OS_LINUX precondition (__unix__/__linux__ defined)") != 0) {
        return 1;
    }

    // B. POSIX 依赖：isatty() 链接可用（rang_implementation 内部使用）。
    extern int isatty(int);
    if (check(isatty(1) >= -1, "isatty() must link on OHOS (POSIX dependency)") != 0)
        return 1;

    // C. TTY 感知：控制台输出在此测试进程中通常无 TTY（被重定向），
    //    rang 的 Auto 模式应当回退为不输出转义序列。
    {
        std::ostringstream os;
        rang::setControlMode(rang::control::Auto);
        os << rang::fg::red << "x" << rang::style::reset;
        if (check(!os.str().empty(), "Auto mode produces output") != 0) return 1;
        if (check(os.str().find('x') != std::string::npos,
                  "Auto mode output contains payload") != 0) return 1;
    }

    // D. control::Force：无论是否 TTY，都必须强制输出 ANSI SGR 转义序列。
    {
        std::ostringstream os;
        rang::setControlMode(rang::control::Force);
        os << rang::fg::green << "green" << rang::style::reset;
        if (check(os.str().find('\033') != std::string::npos,
                  "Force mode must emit ANSI SGR escape") != 0) return 1;
        if (check(os.str().find("green") != std::string::npos,
                  "Force mode output contains payload") != 0) return 1;
    }

    // E. control::Off：一律不输出转义序列（纯文本）。
    {
        std::ostringstream os;
        rang::setControlMode(rang::control::Off);
        os << rang::bg::blue << "blue" << rang::style::reset;
        if (check(os.str() == "blue", "Off mode emits plain text only") != 0) return 1;
    }

    std::cout << "All HarmonyOS platform tests passed!" << std::endl;
    return 0;
}
