/* fmt 9.1.0 consumer test (HarmonyOS PC).
 *
 * 验证 Conan 打包后的 fmt::fmt compiled library，不直接 include 上游源码树。
 * 覆盖：① 基础格式化 ② 位置参数 ③ 数字格式化（浮点精度/科学计数/进制前缀）
 *       ④ format_to/memory_buffer ⑤ fmt/ostream.h fmt::ostream_formatter
 *       ⑥ fmt/ranges.h range 格式化 ⑦ fmt/std.h std::thread::id（9.1.0 提供）
 *       ⑧ compiled library 正确 link ⑨ FMT_VERSION == 90100 (9.1.0)
 *
 * 预期值均按 9.1.0 实际行为（非照抄 8.x/12.x 文档）：
 *   八进制前缀 9.1.0 仍为 "0"（"0o" 前缀是后版本行为）：
 *     {:#o} 8 → "010"
 *   fmt/std.h 在 9.1.0 支持 std::filesystem::path / std::thread::id /
 *   std::monostate / std::variant，尚不支持 std::optional（12.x 才有）。
 */
#include <fmt/format.h>
#include <fmt/ranges.h>     /* fmt::join / range 格式化 */
#include <fmt/ostream.h>    /* fmt::ostream_formatter */
#include <fmt/std.h>        /* std::thread::id / std::filesystem::path 格式化 */

#include <cstdio>
#include <iterator>
#include <ostream>
#include <string>
#include <thread>
#include <vector>

/* CHECK 宏：断言失败则打印 got/want 并返回 1。 */
#define CHECK(label, got, want)                                     \
    do {                                                           \
        if (!((got) == (want))) {                                  \
            std::printf("FAIL %s\n  got:  \"%s\"\n  want: \"%s\"\n", \
                        label, std::string(got).c_str(),            \
                        std::string(want).c_str());                 \
            return 1;                                              \
        }                                                          \
    } while (0)

/* ── ostream_formatter 验证类型 ──
 * 提供 operator<<(std::ostream&, const T&)，再用
 * fmt::formatter<T> : fmt::ostream_formatter 桥接到 fmt::format。
 * 这是下游消费方常用的自定义类型格式化路径。 */
struct Point {
    int x, y;
};
std::ostream& operator<<(std::ostream& os, const Point& p) {
    return os << "(" << p.x << ", " << p.y << ")";
}
template <>
struct fmt::formatter<Point> : fmt::ostream_formatter {};

int main(void) {
    /* ① 基础格式化 + 位置参数 */
    std::string s = fmt::format("{} {}!", "hello", "world");
    CHECK("basic format", s, "hello world!");
    std::string p = fmt::format("{1}-{0}", "a", "b");
    CHECK("positional", p, "b-a");

    /* ② 数字格式化（浮点精度、科学计数、八进制前缀）
     * 八进制前缀按 9.1.0 实际行为：仍是 "0" 而非 "0o"。 */
    std::string f2 = fmt::format("{:.3f}", 3.14159265);
    CHECK("float precision", f2, "3.142");
    std::string e = fmt::format("{:.2e}", 1234.5);
    CHECK("scientific", e, "1.23e+03");
    std::string oct = fmt::format("{:#o}", 8);
    CHECK("octal prefix 9.1.0", oct, "010");

    /* ③ 字符串格式化（对齐与填充） */
    std::string l = fmt::format("[{:<6}]", "ab");
    CHECK("left align", l, "[ab    ]");

    /* ④ format_to / memory_buffer（走与 format() 不同的代码路径） */
    fmt::memory_buffer buf;
    fmt::format_to(std::back_inserter(buf), "{}-{}", 1, 2);
    std::string buf_s(buf.data(), buf.size());
    CHECK("format_to", buf_s, "1-2");

    /* ⑤ ostream_formatter：自定义类型经 operator<< 桥接到 fmt::format
     *    （实证输出 "(1, 2)"） */
    std::string pt = fmt::format("{}", Point{1, 2});
    CHECK("ostream_formatter", pt, "(1, 2)");

    /* ⑥ fmt/ranges.h：range 格式化（9.1.0 提供，实证 "[1, 2, 3]"） */
    std::vector<int> v = {1, 2, 3};
    std::string r = fmt::format("{}", v);
    CHECK("ranges format", r, "[1, 2, 3]");

    /* ⑦ fmt/std.h：std::thread::id 经 fmt/std.h 格式化（9.1.0 支持）
     *    仅验证可编译、可格式化输出非空（线程 id 具体值不可断言）。 */
    std::string tid = fmt::format("{}", std::this_thread::get_id());
    if (tid.empty()) {
        std::printf("FAIL thread::id format: empty output\n");
        return 1;
    }

    /* ⑧ FMT_VERSION 与 9.1.0 对应（FMT_VERSION == 90100） */
    std::string ver = std::to_string(FMT_VERSION);
    CHECK("FMT_VERSION", ver, "90100");

    /* ⑨ compiled library 正确 link —— 程序编译链接运行即证明（隐式）。 */
    std::printf("fmt OK: 9 CHECK passed, FMT_VERSION=%d\n", FMT_VERSION);
    return 0;
}