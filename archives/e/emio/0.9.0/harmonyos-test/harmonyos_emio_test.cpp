// HarmonyOS 专项测试 — emio 0.9.0 (C++20 header-only I/O library).
//
// 覆盖 OHOS 平台下 emio 真实 API 的编译与运行正确性：
//   1. UTF-8 字符串格式化（OHOS 默认 UTF-8 文本域）
//   2. 整数/十六进制格式输出（静态 buffer，无堆分配，适合 RTOS/嵌入式语义）
//   3. 低层 writer/reader 往返（字节级 I/O，非空壳）
//   4. OHOS aarch64 目标下 std::string_view / char 语义正确性
#include <cassert>
#include <string>

#include <emio/emio.hpp>

int main() {
    // 1) 高精度格式：整数格式化（OHOS 常用 %d 语义）
    {
        const std::string s = emio::format("{}", 42);
        assert(s == "42");
        const std::string h = emio::format("{:#x}", 42);
        assert(h == "0x2a");
    }

    // 2) 无堆静态 buffer 格式化（嵌入式语义）
    {
        emio::static_buffer<64> buf{};
        assert(emio::format_to(buf, "v={}", 1.5).has_value());
        assert(buf.view() == "v=1.5");
    }

    // 3) 低层 writer（写入）→ reader（读回）往返
    {
        emio::static_buffer<64> buf{};
        emio::writer w{buf};
        assert(w.write_str("id=").has_value());
        assert(w.write_int(17).has_value());
        assert(w.write_char('!').has_value());

        emio::reader r{buf.view()};
        auto prefix = r.read_n_chars(3);  // consume "id="
        auto id = r.parse_int<int>();
        auto ch = r.read_char();
        assert(prefix.has_value() && *prefix == "id=");
        assert(id.has_value() && *id == 17);
        assert(ch.has_value() && *ch == '!');
    }

    // 4) UTF-8 文本与 string_view 兼容（OHOS 平台字符域）
    {
        const std::string utf8 = emio::format("{}", "hello 世界");
        assert(utf8 == "hello 世界");
        const std::string sv_str = emio::format("{}", std::string_view{"ok"});
        assert(std::string_view{sv_str} == "ok");
    }

    // 5) scan 反向解析（输入解析）
    {
        int a{};
        char c{};
        emio::result<void> res = emio::scan("17c", "{}{}", a, c);
        assert(res.has_value());
        assert(a == 17 && c == 'c');
    }

    return 0;
}