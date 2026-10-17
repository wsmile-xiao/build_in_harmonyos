// bobcat 6.14.00 消费者测试：链接 libbobcat.so，真实调用公开 API 并断言行为
// 覆盖：异常流式构造、DateTime、Pattern 正则、String::split、Glob、
//       Process 子进程（fork/exec + 管道提取 child stdout）
#include <bobcat/exception>
#include <bobcat/datetime>
#include <bobcat/pattern>
#include <bobcat/string>
#include <bobcat/glob>
#include <bobcat/process>
#include <bobcat/processenums>

#include <iostream>
#include <sstream>
#include <string>
#include <vector>

static int g_checks = 0;

#define CHECK(cond, msg)                                     \
    do                                                       \
    {                                                        \
        if (!(cond))                                         \
        {                                                    \
            std::cerr << "FAIL: " << msg << " (line "        \
                      << __LINE__ << ")\n";                  \
            return 1;                                        \
        }                                                    \
        ++g_checks;                                          \
    } while (0)

int main()
{
    // 1. Exception: 流式构造 + what()
    try
    {
        throw FBB::Exception{} << "answer=" << 42;
    }
    catch (std::exception const &ex)
    {
        std::string const what = ex.what();
        CHECK(what.find("answer=42") != std::string::npos,
              "Exception message propagation");
    }

    // 2. DateTime: epoch 构造与字段提取（UTC 1970-01-01 00:00:00）
    FBB::DateTime epoch(0, FBB::DateTime::UTC);
    CHECK(epoch.year() == 1970, "DateTime year");
    CHECK(epoch.hours() == 0 && epoch.minutes() == 0, "DateTime time fields");

    // 3. DateTime 流插入
    {
        std::stringstream out;
        out << epoch;
        CHECK(out.str().find("1970") != std::string::npos,
              "DateTime stream insertion");
    }

    // 4. Pattern: 正则匹配与捕获组
    FBB::Pattern pat(R"(^([a-z]+)-([0-9]+)$)");
    CHECK(pat << "bobcat-61400", "Pattern match");
    CHECK(pat[1] == "bobcat" && pat[2] == "61400", "Pattern capture groups");

    // 5. String::split（TOK 语义）
    {
        FBB::String::Type type;
        std::vector<std::string> parts =
            FBB::String::split(&type, "a:b:c", FBB::String::TOK, ":");
        CHECK(parts.size() == 3, "String split count");
        CHECK(parts[0] == "a" && parts[2] == "c", "String split content");
    }

    // 6. Glob: 当前目录能匹配到条目
    {
        FBB::Glob glob("*");
        CHECK(glob.size() > 0, "Glob returns entries");
    }

    // 7. Process: 真实 fork/exec 子进程，捕获其 stdout（库的核心能力）
    {
        FBB::Process process(FBB::Process::COUT,
                             "/bin/sh -c \"printf 'bobcat-ohos'\"");
        process.start();
        std::string line;
        std::getline(process.childOutStream(), line);
        int ret = process.stop();
        CHECK(ret == 0, "Process child exit status");
        CHECK(line == "bobcat-ohos", "Process child stdout captured");
    }

    std::cout << "consumer OK: " << g_checks << " checks passed\n";
    return 0;
}
