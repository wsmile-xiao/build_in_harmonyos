/**
 * 消费者测试 — tclap 1.2.5（header-only 交付形态）
 *
 * 用法: test_tclap <conan-package-folder>
 * 由 test_package/conanfile.py 的 test() 传入 self.dependencies["tclap"].package_folder，
 * 直接对**实际交付的包目录**断言（§二.19：头文件/单文件包必须断言「打包的就是那一份」）。
 *
 * A. 交付面指纹（读包目录）
 *    1. include/tclap 头文件数 == 25
 *    2. include/tclap/CmdLine.h 字节数 == 14764（与上游 tag v1.2.5 同源指纹）
 *    3. CmdLine.h 内含上游 include guard `TCLAP_CMDLINE_H` 与版权行 Michael E. Smoot
 *    4. 包内无 lib/ 产物（header-only：package_type=header-library）
 *    5. licenses/COPYING 已交付
 *
 * B. 解析行为（真实 include <tclap/CmdLine.h> 并调用 API）
 *    6. ValueArg<string> 必填项取到解析值 "mike"
 *    7. SwitchArg 未置位时为 false
 *    8. SwitchArg 被 -r 置位后为 true
 *    9. MultiArg 收集 3 个值
 *   10. int 类型转换取到 42
 *   11. 缺必填项抛 ArgException
 *
 * 断言口径：11 条运行期断言；逐条打印读数，任一失败退出码非 0。
 */
#include <tclap/CmdLine.h>

#include <cstdio>
#include <cstring>
#include <fstream>
#include <iterator>
#include <string>

#if defined(_WIN32)
#include <direct.h>
#define TCLAP_ACCESS(p) (_access((p), 0) == 0)
#else
#include <unistd.h>
#define TCLAP_ACCESS(p) (access((p), F_OK) == 0)
#endif

static int g_total = 0;
static int g_failed = 0;

static void Check(const char * name, const std::string & got,
                  const std::string & want)
{
    ++g_total;
    if (got == want)
        std::printf("[consumer] PASS  %-56s got=%s\n", name, got.c_str());
    else
    {
        ++g_failed;
        std::printf("[consumer] FAIL  %-56s got=%s want=%s\n", name,
                    got.c_str(), want.c_str());
    }
}

static void CheckInt(const char * name, long got, long want)
{
    ++g_total;
    if (got == want)
        std::printf("[consumer] PASS  %-56s got=%ld\n", name, got);
    else
    {
        ++g_failed;
        std::printf("[consumer] FAIL  %-56s got=%ld want=%ld\n", name, got,
                    want);
    }
}

static long FileSize(const std::string & path)
{
    std::ifstream in(path.c_str(), std::ios::binary | std::ios::ate);
    if (!in)
        return -1;
    return static_cast<long>(in.tellg());
}

/* 上游 tag v1.2.5 的 include/tclap 头文件清单（25 个）——逐个存在才算齐 */
static long CountHeaders(const std::string & dir)
{
    static const char * NAMES[] = {
        "Arg.h",                  "ArgException.h",
        "ArgTraits.h",            "CmdLine.h",
        "CmdLineInterface.h",     "CmdLineOutput.h",
        "Constraint.h",           "DocBookOutput.h",
        "HelpVisitor.h",          "IgnoreRestVisitor.h",
        "MultiArg.h",             "MultiSwitchArg.h",
        "OptionalUnlabeledTracker.h", "StandardTraits.h",
        "StdOutput.h",            "SwitchArg.h",
        "UnlabeledMultiArg.h",    "UnlabeledValueArg.h",
        "ValueArg.h",             "ValuesConstraint.h",
        "VersionVisitor.h",       "Visitor.h",
        "XorHandler.h",           "ZshCompletionOutput.h",
        "sstream.h"
    };
    const long n = static_cast<long>(sizeof(NAMES) / sizeof(NAMES[0]));
    long present = 0;
    for (long i = 0; i < n; ++i)
    {
        std::ifstream in((dir + "/" + NAMES[i]).c_str());
        if (in)
            ++present;
    }
    return present;
}

int main(int argc, char ** argv)
{
    if (argc < 2)
    {
        std::printf("usage: test_tclap <conan-package-folder>\n");
        return 2;
    }
    const std::string root = argv[1];
    const std::string inc = root + "/include";

    // ── A. 交付面指纹 ───────────────────────────────────────────────
    CheckInt("packaged headers under include/tclap == 25",
             CountHeaders(inc + "/tclap"), 25);
    CheckInt("include/tclap/CmdLine.h bytes == 14764 (upstream v1.2.5)",
             FileSize(inc + "/tclap/CmdLine.h"), 14764);
    {
        // 读整个头文件核上游身份（首行是 emacs mode 行；用 include guard + 版权行做指纹）
        std::ifstream in((inc + "/tclap/CmdLine.h").c_str(),
                         std::ios::binary);
        std::string all((std::istreambuf_iterator<char>(in)),
                        std::istreambuf_iterator<char>());
        Check("tclap/CmdLine.h carries upstream include guard + copyright",
              (all.find("TCLAP_CMDLINE_H") != std::string::npos &&
               all.find("Michael E. Smoot") != std::string::npos)
                  ? "found"
                  : "missing",
              "found");
    }
    CheckInt("header-only: package has no lib/ dir",
             TCLAP_ACCESS((root + "/lib").c_str()) ? 1 : 0, 0);
    CheckInt("licenses/COPYING delivered",
             TCLAP_ACCESS((root + "/licenses/COPYING").c_str()) ? 1 : 0, 1);

    // ── B. 解析行为 ─────────────────────────────────────────────────
    try
    {
        TCLAP::CmdLine cmd1("consumer", ' ', "1.2.5");
        TCLAP::ValueArg<std::string> name("n", "name", "name", true, "",
                                          "string");
        cmd1.add(name);
        char a0[] = "prog";
        char a1[] = "-n";
        char a2[] = "mike";
        char * av1[] = { a0, a1, a2 };
        int ac1 = 3;
        cmd1.parse(ac1, av1);
        Check("ValueArg<string> parsed value == mike", name.getValue(), "mike");
    }
    catch (const TCLAP::ArgException & e)
    {
        Check("ValueArg<string> parsed value == mike",
              std::string("exception:") + e.what(), "mike");
    }

    try
    {
        TCLAP::CmdLine cmd2("consumer", ' ', "1.2.5");
        TCLAP::SwitchArg verbose("v", "verbose", "verbose", false);
        cmd2.add(verbose);
        char a0[] = "prog";
        char * av2[] = { a0 };
        int ac2 = 1;
        cmd2.parse(ac2, av2);
        CheckInt("SwitchArg unset after parse == false",
                 verbose.getValue() ? 1 : 0, 0);
    }
    catch (const TCLAP::ArgException & e)
    {
        Check("SwitchArg unset after parse == false",
              std::string("exception:") + e.what(), "0");
    }

    try
    {
        TCLAP::CmdLine cmd3("consumer", ' ', "1.2.5");
        TCLAP::SwitchArg reverse("r", "reverse", "reverse", false);
        cmd3.add(reverse);
        char a0[] = "prog";
        char a1[] = "-r";
        char * av3[] = { a0, a1 };
        int ac3 = 2;
        cmd3.parse(ac3, av3);
        CheckInt("SwitchArg set by -r == true", reverse.getValue() ? 1 : 0, 1);
    }
    catch (const TCLAP::ArgException & e)
    {
        Check("SwitchArg set by -r == true",
              std::string("exception:") + e.what(), "1");
    }

    try
    {
        TCLAP::CmdLine cmd4("consumer", ' ', "1.2.5");
        TCLAP::MultiArg<std::string> item("i", "item", "repeatable", false,
                                          "string");
        cmd4.add(item);
        char a0[] = "prog";
        char a1[] = "-i";
        char a2[] = "one";
        char a3[] = "-i";
        char a4[] = "two";
        char a5[] = "-i";
        char a6[] = "three";
        char * av4[] = { a0, a1, a2, a3, a4, a5, a6 };
        int ac4 = 7;
        cmd4.parse(ac4, av4);
        CheckInt("MultiArg collected 3 values",
                 static_cast<long>(item.getValue().size()), 3);
    }
    catch (const TCLAP::ArgException & e)
    {
        Check("MultiArg collected 3 values",
              std::string("exception:") + e.what(), "3");
    }

    try
    {
        TCLAP::CmdLine cmd5("consumer", ' ', "1.2.5");
        TCLAP::ValueArg<int> count("", "count", "count", true, 0, "int");
        cmd5.add(count);
        char a0[] = "prog";
        char a1[] = "--count";
        char a2[] = "42";
        char * av5[] = { a0, a1, a2 };
        int ac5 = 3;
        cmd5.parse(ac5, av5);
        CheckInt("ValueArg<int> conversion == 42", count.getValue(), 42);
    }
    catch (const TCLAP::ArgException & e)
    {
        Check("ValueArg<int> conversion == 42",
              std::string("exception:") + e.what(), "42");
    }

    try
    {
        TCLAP::CmdLine cmd6("consumer", ' ', "1.2.5");
        TCLAP::ValueArg<std::string> required("n", "name", "required", true,
                                              "", "string");
        cmd6.add(required);
        // 默认 exceptionHandling=true 时 CmdLine 自己打印 PARSE ERROR 并 exit(1)；
        // 关掉它才能在本进程里 catch 到 ArgException（第 506/518 行分支）
        cmd6.setExceptionHandling(false);
        char a0[] = "prog";
        char * av6[] = { a0 };
        int ac6 = 1;
        cmd6.parse(ac6, av6);
        Check("missing required ValueArg throws ArgException", "no-exception",
              "thrown");
    }
    catch (const TCLAP::ArgException &)
    {
        Check("missing required ValueArg throws ArgException", "thrown",
              "thrown");
    }

    std::printf("[consumer] summary: %d/%d assertions passed\n",
                g_total - g_failed, g_total);
    return g_failed == 0 ? 0 : 1;
}
