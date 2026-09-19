/***************************************************************************
 * test_origin2.cpp — liborigin2 消费者测试（HarmonyOS 增量验证）
 *
 * 只使用已安装的公共头与库（OriginFile.h → include/liborigin2/），不接触上游
 * 源码树。测试构造真实的 .opj 文件头来做功能验证：
 * OriginFile 的构造函数会读取文件偏移 0x7 起的 4 个 ASCII 字节作为 build
 * version，再映射成 OriginFile::version()（fileVersion/100.0）并据此挑选解析器。
 * 因此合成一个只含版本号的文件头，就能驱动库的真实代码路径（版本映射 +
 * 解析器工厂），而不是只做一次空壳链接。
 ***************************************************************************/
#include <cstring>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>

#include "OriginFile.h"

static int failures = 0;

static void check(bool ok, const std::string& what)
{
    std::cout << (ok ? "  ok   " : "  FAIL ") << what << std::endl;
    if (!ok)
        ++failures;
}

/* 生成一个只带 .opj 版本头的合成文件：偏移 0x7 处写入 4 个 ASCII 数字。
 * 填充字节必须是空白字符：库用 `file >> vers` 读这 4 个字节，读到第一个空白
 * 才停下，否则会把填充内容一并读入导致 lexical_cast 失败。 */
static std::string make_opj(const std::string& tag, unsigned char filler)
{
    std::string path = "synthetic-" + tag + ".opj";
    std::string data(4096, static_cast<char>(filler));
    std::memcpy(&data[7], tag.data(), 4);
    std::ofstream out(path.c_str(), std::ios::binary);
    out.write(data.data(), static_cast<std::streamsize>(data.size()));
    out.close();
    return path;
}

int main()
{
    std::cout << "[liborigin2] LIBORIGIN_VERSION_STRING = "
              << LIBORIGIN_VERSION_STRING << std::endl;

    /* 1. Origin 8.1（文件头 2907）→ version() == 8.1，走 810 解析器工厂 */
    try {
        const std::string path = make_opj("2907", 0x20);
        OriginFile f(path);
        check(f.version() == 8.1, "Origin 8.1 header -> version() == 8.1");
        check(f.spreadCount() == 0, "spreadCount() == 0 (unparsed file)");
        check(f.matrixCount() == 0, "matrixCount() == 0 (unparsed file)");
        check(f.graphCount() == 0, "graphCount() == 0 (unparsed file)");
        check(f.noteCount() == 0, "noteCount() == 0 (unparsed file)");
        check(f.project() != nullptr, "project() returns a project tree");
        /* 合成的文件体不是合法 .opj 内容：parse() 必须能安全返回而不是崩溃
         * （实测对全是空白的文件体返回 true —— 这里只断言"不抛异常、能返回"，
         *   不对上游在垃圾输入上的返回值做强假设）。 */
        bool parsed = false;
        bool parse_threw = false;
        try {
            parsed = f.parse();
        } catch (const std::exception&) {
            parse_threw = true;
        }
        check(!parse_threw, "parse() returns without throwing on a truncated file"
                            " (returned " + std::string(parsed ? "true" : "false") + ")");
    } catch (const std::exception& e) {
        check(false, std::string("Origin 8.1 path threw: ") + e.what());
    }

    /* 2. Origin 6.1（文件头 2635）→ version() == 6.1，走 610 解析器工厂 */
    try {
        const std::string path = make_opj("2635", 0x20);
        OriginFile f(path);
        check(f.version() == 6.1, "Origin 6.1 header -> version() == 6.1");
    } catch (const std::exception& e) {
        check(false, std::string("Origin 6.1 path threw: ") + e.what());
    }

    /* 3. 未知版本必须抛 std::logic_error（上游定义的失败路径） */
    {
        const std::string path = make_opj("0001", 0x20);
        bool threw = false;
        std::string what;
        try {
            OriginFile f(path);
            (void)f;
        } catch (const std::logic_error& e) {
            threw = true;
            what = e.what();
        } catch (const std::exception& e) {
            what = e.what();
        }
        check(threw, "unknown build version throws std::logic_error"
                     + (what.empty() ? std::string() : " (" + what + ")"));
    }

    /* 4. 打不开的文件：构造函数不得抛异常（只打印告警后返回） */
    {
        bool threw = false;
        try {
            OriginFile f("definitely-not-here-4711.opj");
            (void)f;
        } catch (const std::exception&) {
            threw = true;
        }
        check(!threw, "missing file does not throw from the constructor");
    }

    if (failures == 0) {
        std::cout << "test_origin2: ALL CHECKS PASSED" << std::endl;
        return 0;
    }
    std::cout << "test_origin2: " << failures << " CHECK(S) FAILED" << std::endl;
    return 1;
}
