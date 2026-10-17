/* fmt 8.1.1 真实功能断言。
 *
 * 不用 dlopen 探针：解析到符号 ≠ 格式化结果对。这里断言**输出字符串本身**，
 * 覆盖 fmt 的几条核心契约：位置参数、具名参数、对齐/填充、精度、进制、
 * 以及 8.x 才有的编译期格式串检查路径（FMT_STRING）。
 *
 * 之所以钉在 8.x：下游 ad-map-access 的 .so 依赖 libfmt.so.8，
 * 且 fmt 9/10/11 删改过 API，换大版本源码未必编得过。
 */
#include <fmt/format.h>
/* ⚠️ 不要 include <fmt/chrono.h>：它拉进 libc++ 的 <locale>，
 * 而鸿蒙 musl 没有 uselocale / LC_*_MASK，编译期直接报
 * `use of undeclared identifier 'uselocale'`。
 * 那是 libc++ 与 musl 的已知缺口，与 fmt 本身无关；本测试也用不到时间格式化。 */

#include <cstdio>
#include <iterator>   /* back_inserter */
#include <string>

static int fail(const char *what, const std::string &got, const std::string &want)
{
    std::printf("FAIL %s\n  实得: %s\n  期望: %s\n", what, got.c_str(), want.c_str());
    return 1;
}

int main(void)
{
    /* ① 基本替换与位置参数 */
    {
        std::string s = fmt::format("{} {}!", "hello", "world");
        if (s != "hello world!") return fail("基本替换", s, "hello world!");
        std::string p = fmt::format("{1}-{0}", "a", "b");
        if (p != "b-a") return fail("位置参数", p, "b-a");
    }

    /* ② 具名参数 */
    {
        std::string s = fmt::format("{name} is {age}", fmt::arg("name", "kdl"),
                                    fmt::arg("age", 42));
        if (s != "kdl is 42") return fail("具名参数", s, "kdl is 42");
    }

    /* ③ 对齐与填充——宽度/填充字符的语义容易在移植中出偏差 */
    {
        std::string l = fmt::format("[{:<6}]", "ab");
        std::string r = fmt::format("[{:>6}]", "ab");
        std::string c = fmt::format("[{:^6}]", "ab");
        std::string z = fmt::format("[{:*^6}]", "ab");
        if (l != "[ab    ]") return fail("左对齐", l, "[ab    ]");
        if (r != "[    ab]") return fail("右对齐", r, "[    ab]");
        if (c != "[  ab  ]") return fail("居中", c, "[  ab  ]");
        if (z != "[**ab**]") return fail("填充字符", z, "[**ab**]");
    }

    /* ④ 数值精度与进制——浮点格式化是最容易因 libc 差异出问题的一块 */
    {
        std::string f2 = fmt::format("{:.3f}", 3.14159265);
        if (f2 != "3.142") return fail("浮点精度", f2, "3.142");
        std::string e = fmt::format("{:.2e}", 1234.5);
        if (e != "1.23e+03") return fail("科学计数", e, "1.23e+03");
        /* ⚠️ fmt 8.x 的八进制前缀是 "0"（如 010），`0o` 是 fmt 9+ 才改的。
         * 断言必须钉在**本版本的实际行为**上，不能照抄新版文档。 */
        std::string hx = fmt::format("{:#x} {:#o} {:#b}", 255, 8, 5);
        if (hx != "0xff 010 0b101") return fail("进制前缀", hx, "0xff 010 0b101");
    }

    /* ⑤ 千位分隔与符号 */
    {
        std::string n = fmt::format("{:+d} {:d}", 42, -42);
        if (n != "+42 -42") return fail("符号", n, "+42 -42");
    }

    /* ⑥ format_to 到缓冲区——走的是与 format() 不同的代码路径 */
    {
        fmt::memory_buffer buf;
        fmt::format_to(std::back_inserter(buf), "{}-{}", 1, 2);
        std::string s(buf.data(), buf.size());
        if (s != "1-2") return fail("format_to", s, "1-2");
    }

    /* ⑦ 编译期格式串检查（8.x 的 FMT_STRING 路径）*/
    {
        std::string s = fmt::format(FMT_STRING("{:d}"), 7);
        if (s != "7") return fail("FMT_STRING", s, "7");
    }

    /* ⑧ 版本确认：下游按 libfmt.so.8 链接，主版本必须是 8 */
    {
        const int major = FMT_VERSION / 10000;
        if (major != 8) {
            std::printf("FAIL fmt 主版本为 %d，期望 8（下游依赖 libfmt.so.8）\n", major);
            return 1;
        }
    }

    std::printf("fmt OK: 替换/位置/具名/对齐/精度/进制/format_to/FMT_STRING 共 8 组，版本 %d\n",
                FMT_VERSION);
    return 0;
}
