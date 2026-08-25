/* fmt 12.2.0 consumer test (HarmonyOS PC).
 *
 * 验证 Conan 打包后的 fmt::fmt compiled library，不直接 include 上游源码树。
 * 覆盖：① 基础格式化 ② 数字格式化 ③ 字符串格式化 ④ format_to/memory_buffer
 *       ⑤ fmt/std.h 可 include ⑥ fmt::ostream_formatter 可用
 *       ⑦ std 类型经 fmt/std.h 格式化 ⑧ compiled library 正确 link
 *       ⑨ FMT_VERSION == 120200 (12.2.0)
 *
 * 预期值均经 OHOS toolchain 实证（非照抄文档）：
 *   std::optional<double>(1.5) → "optional(1.5)"
 *   Point{1,2} via ostream_formatter → "(1, 2)"
 *   {:#o} 8 → "010"（12.x 八进制前缀仍为 "0"，非 "0o"）
 */
#include <fmt/format.h>
#include <fmt/std.h>        /* std::optional formatter（12.2.0 起 std::byte 也在其中）*/
#include <fmt/ostream.h>    /* fmt::ostream_formatter */

#include <cstdio>
#include <iterator>
#include <optional>
#include <ostream>
#include <string>

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
 * 这是 mitama-cpp-result 后续依赖 fmt/12.2.0 的关键 API。 */
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

    /* ② 数字格式化（浮点精度、科学计数、进制前缀）
     * 进制前缀按 12.x 实际行为：八进制是 "0" 而非 "0o"（OHOS 实证）。 */
    std::string f2 = fmt::format("{:.3f}", 3.14159265);
    CHECK("float precision", f2, "3.142");
    std::string e = fmt::format("{:.2e}", 1234.5);
    CHECK("scientific", e, "1.23e+03");
    std::string oct = fmt::format("{:#o}", 8);
    CHECK("octal prefix 12.x", oct, "010");

    /* ③ 字符串格式化（对齐与填充） */
    std::string l = fmt::format("[{:<6}]", "ab");
    CHECK("left align", l, "[ab    ]");

    /* ④ format_to / memory_buffer（走与 format() 不同的代码路径） */
    fmt::memory_buffer buf;
    fmt::format_to(std::back_inserter(buf), "{}-{}", 1, 2);
    std::string buf_s(buf.data(), buf.size());
    CHECK("format_to", buf_s, "1-2");

    /* ⑤⑥⑦ fmt/std.h：std::optional 经 fmt/std.h 格式化
     *    （实证输出 "optional(1.5)"，空 optional 为 "none"） */
    std::string opt = fmt::format("{}", std::optional<double>(1.5));
    CHECK("std::optional via fmt/std.h", opt, "optional(1.5)");

    /* ⑧ ostream_formatter：自定义类型经 operator<< 桥接到 fmt::format
     *    （实证输出 "(1, 2)"） */
    std::string pt = fmt::format("{}", Point{1, 2});
    CHECK("ostream_formatter", pt, "(1, 2)");

    /* ⑨ FMT_VERSION 与 12.2.0 对应（FMT_VERSION == 120200） */
    std::string ver = std::to_string(FMT_VERSION);
    CHECK("FMT_VERSION", ver, "120200");

    /* ⑩ compiled library 正确 link —— 程序编译链接运行即证明（隐式）。 */
    std::printf("fmt OK: 10 CHECK passed, FMT_VERSION=%d\n", FMT_VERSION);
    return 0;
}
