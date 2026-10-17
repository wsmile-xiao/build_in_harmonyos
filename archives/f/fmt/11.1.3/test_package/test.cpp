/* fmt 11.1.3 consumer test (HarmonyOS PC) — test_package 消费者验证。
 *
 * 验证 Conan 打包后的 fmt::fmt compiled library（不直接 include 上游源码树）。
 * 覆盖：① 基础格式化+位置参数 ② 数字/浮点/进制/对齐 ③ format_to/memory_buffer
 *       ④ fmt::printf ⑤ fmt::join(ranges) ⑥ chrono 时间点 ⑦ fmt/std.h optional
 *       ⑧ fmt::to_wstring(xchar 宽字符) ⑨ fmt/color.h 颜色输出 ⑩ FMT_VERSION == 110103
 *       ⑪ ostream_formatter 桥接自定义类型（后续依赖方关键 API）
 *
 * 预期值均经 OHOS 工具链实证（非照抄文档）：
 *   11.x 八进制前缀为 "0"（非 "0o"）；time_point 默认附加微秒精度。
 */
#include <fmt/format.h>
#include <fmt/printf.h>
#include <fmt/xchar.h>
#include <fmt/color.h>
#include <fmt/chrono.h>
#include <fmt/ranges.h>
#include <fmt/std.h>
#include <fmt/ostream.h>

#include <cstdio>
#include <iterator>
#include <optional>
#include <ostream>
#include <string>
#include <vector>
#include <chrono>

#define CHECK(label, got, want)                                     \
    do {                                                            \
        if (!((got) == (want))) {                                   \
            std::printf("FAIL %s\n  got:  \"%s\"\n  want: \"%s\"\n", \
                        label, std::string(got).c_str(),            \
                        std::string(want).c_str());                 \
            return 1;                                               \
        }                                                           \
    } while (0)

/* ostream_formatter 桥接类型（fmt/ostream.h + fmt 11.x 惯例） */
struct Point {
    int x, y;
};
std::ostream& operator<<(std::ostream& os, const Point& p) {
    return os << "(" << p.x << ", " << p.y << ")";
}
template <>
struct fmt::formatter<Point> : fmt::ostream_formatter {};

int main() {
    /* ① 基础格式化 + 位置参数 */
    std::string s = fmt::format("{} {}!", "hello", "world");
    CHECK("basic format", s, "hello world!");
    std::string p = fmt::format("{1}-{0}", "a", "b");
    CHECK("positional", p, "b-a");

    /* ② 数字格式化 */
    std::string f2 = fmt::format("{:.3f}", 3.14159265);
    CHECK("float precision", f2, "3.142");
    std::string e = fmt::format("{:.2e}", 1234.5);
    CHECK("scientific", e, "1.23e+03");
    std::string oct = fmt::format("{:#o}", 8);
    CHECK("octal prefix 11.x", oct, "010");
    std::string hx = fmt::format("{:#x}", 255);
    CHECK("hex", hx, "0xff");
    std::string l = fmt::format("[{:<6}]", "ab");
    CHECK("left align", l, "[ab    ]");

    /* ③ format_to / memory_buffer */
    fmt::memory_buffer buf;
    fmt::format_to(std::back_inserter(buf), "{}-{}", 1, 2);
    std::string buf_s(buf.data(), buf.size());
    CHECK("format_to", buf_s, "1-2");

    /* ④ fmt::sprintf */
    CHECK("sprintf", fmt::sprintf("%s-%d", "fmt", 42), "fmt-42");

    /* ⑤ fmt::join (ranges) */
    std::vector<int> v{1, 2, 3};
    CHECK("join", fmt::format("{}", fmt::join(v, ",")), "1,2,3");

    /* ⑥ chrono 时间点（11.x 默认微秒精度） */
    auto tp = std::chrono::system_clock::from_time_t(0);
    CHECK("chrono epoch", fmt::format("{:%Y-%m-%d %H:%M:%S}", tp),
          "1970-01-01 00:00:00.000000");

    /* ⑦ fmt/std.h：std::optional */
    CHECK("std::optional", fmt::format("{}", std::optional<double>(1.5)),
          "optional(1.5)");

    /* ⑧ fmt/xchar.h：宽字符 */
    std::wstring ws = fmt::to_wstring(42);
    std::string ws_repr;
    for (wchar_t c : ws) ws_repr.push_back(static_cast<char>(c));
    CHECK("to_wstring", ws_repr, "42");

    /* ⑨ fmt/color.h：OHOS 下执行不崩溃 */
    try {
        fmt::print(fg(fmt::color::green), "fmt-color-ok\n");
    } catch (...) {
        CHECK("color print", "exception", "ok");
    }

    /* ⑩ FMT_VERSION == 110103 (11.1.3) */
    std::string ver = std::to_string(FMT_VERSION);
    CHECK("FMT_VERSION", ver, "110103");

    /* ⑪ ostream_formatter 桥接 */
    std::string pt = fmt::format("{}", Point{1, 2});
    CHECK("ostream_formatter", pt, "(1, 2)");

    std::printf("fmt 11.1.3 OK: 11 CHECK passed, FMT_VERSION=%d\n", FMT_VERSION);
    return 0;
}