/* uni-algo 1.2.0 鸿蒙（OHOS）专项测试
 *
 * 这里只放「换平台就可能变」的断言，全部通过包内 libuni-algo.a 的 Unicode 数据表求值：
 *  1) OHOS aarch64 工具链/ABI 证据：__OHOS__ / __aarch64__ / LP64 / wchar_t 宽度。
 *     uni-algo 的 utf32to8(std::wstring_view) 重载只有在 wchar_t 是 32 位时才表示 UTF-32，
 *     这正是平台相关语义（Windows 上同一个重载是 UTF-16）。
 *  2) musl 的 locale 环境：setlocale(LC_ALL,"") 后 nl_langinfo(CODESET) 必须是 UTF-8，
 *     这是本包在鸿蒙上按 UTF-8 处理文本的前提；glibc 机器上它会随 LANG 变。
 *  3) una::locale::system() 在鸿蒙（LANG 常为空）下能正常解析并参与大小写映射，不抛异常。
 *  4) 含组合序列的非 ASCII 文件名在鸿蒙文件系统上的真实创建/枚举/读写：
 *     断言 readdir 回来的字节序列与我们写入的 NFD 名字逐字节相等，
 *     即鸿蒙文件系统**不做**文件名 Unicode 归一化（macOS HFS+ 会偷偷转 NFD，这里必须自己判）。
 *  5) 大缓冲（32768 码点 / 98304 字节）转换、逐字素计数与 NFC 幂等。
 */
#include <dirent.h>

#include <cstdio>
#include <cstring>
#include <clocale>
#include <iostream>
#include <string>
#include <vector>

// langinfo.h 是 POSIX/musl 有的头，Windows 主机没有；用 __has_include 让本文件
// 在非目标平台上也能编起来跑其余断言（真机上恒定存在，codeset 断言照常生效）。
#if defined(__has_include)
#  if __has_include(<langinfo.h>)
#    include <langinfo.h>
#    define UNI_ALGO_HAVE_LANGINFO 1
#  endif
#endif

#include <uni_algo/all.h>
#include <uni_algo/locale.h>

static int g_total = 0;
static int g_pass = 0;

// 变参形式：断言表达式里的逗号（如 std::strcmp(a, b)）会被当成宏参数分隔符
#define CHECK(...)                                                                 \
    do {                                                                           \
        ++g_total;                                                                 \
        if (__VA_ARGS__) { ++g_pass; }                                             \
        else { std::cout << "CHECK FAILED: " #__VA_ARGS__ " @line " << __LINE__ << '\n'; } \
    } while (0)

static int count_graphemes(const std::string& s)
{
    int n = 0;
    auto view = una::ranges::grapheme::utf8_view{s};
    for (auto it = view.begin(); it != view.end(); ++it)
        ++n;
    return n;
}

// 测 (U+6D4B) 的 UTF-8 字节
static const char kCjk1[] = "\xE6\xB5\x8B";

int main()
{
    std::cout << "uni-algo OHOS special probe\n";

    // ---- 1) 平台/ABI 证据 ----
#ifdef __OHOS__
    const bool ohos_macro = true;
#else
    const bool ohos_macro = false;
#endif
#ifdef __aarch64__
    const bool aarch64_macro = true;
#else
    const bool aarch64_macro = false;
#endif
    CHECK(ohos_macro);
    CHECK(aarch64_macro);
    CHECK(sizeof(void*) == 8);
    // OHOS aarch64 上 wchar_t 是 32 位 -> std::wstring 存 UTF-32，
    // utf32to8(std::wstring_view) 重载语义与 Windows(16 位) 不同。
    CHECK(sizeof(wchar_t) == 4);
    // 上游用 WCHAR_MAX >= 0x7FFFFFFF 决定该重载是否存在，这里同条件保护，
    // 让本文件在非目标平台也能编起来跑其余断言（真机上一定生效）。
#if WCHAR_MAX >= 0x7FFFFFFF
    {
        const std::wstring w = std::wstring(L"\x5B57") + wchar_t(0x1F63A);
        const std::string via_wstring = una::utf32to8(w);
        CHECK(via_wstring == std::string("\xE5\xAD\x97") + "\U0001F63A");
        CHECK(una::utf16to8(una::utf8to16u(via_wstring)) == via_wstring);
    }
#endif

    // ---- 2) musl locale / codeset ----
#ifdef UNI_ALGO_HAVE_LANGINFO
    {
        const char* reset = std::setlocale(LC_ALL, "");
        CHECK(reset != nullptr);
        // musl 的 <langinfo.h> 只声明全局 nl_langinfo，libc++ 也不会把它搬进 std::
        const char* cs = nl_langinfo(CODESET);
        std::cout << "  platform codeset = " << (cs ? cs : "(null)") << '\n';
        CHECK(cs != nullptr && std::strcmp(cs, "UTF-8") == 0);
    }
#else
    std::cout << "  (no langinfo.h on this host: codeset assertions compiled out)\n";
#endif

    // ---- 3) 系统 locale 参与大小写映射（鸿蒙上 LANG 通常为空的场景） ----
    {
        const una::locale sys = una::locale::system();
        std::cout << "  una::locale::system() = \"" << sys.to_string() << "\"\n";
        CHECK(una::cases::to_uppercase_utf8("Test", sys) == "TEST");
        // 系统 locale 为空也不能影响与 locale 无关的默认映射
        CHECK(una::cases::to_lowercase_utf8("\xD0\x94\xD0\x92\xD0\x90", sys) ==
              "\xD0\xB4\xD0\xB2\xD0\xB0");
    }

    // ---- 4) 含组合序列的非 ASCII 文件名在鸿蒙文件系统上的行为 ----
    // NFD: Cafe + COMBINING ACUTE ACCENT；NFC: Caf + U+00E9
    const std::string nfd_name =
        std::string("uni-algo11505-") + kCjk1 + "\xE8\xAF\x95-Cafe\xCC\x81.txt";
    const std::string nfc_name =
        std::string("uni-algo11505-") + kCjk1 + "\xE8\xAF\x95-Caf\xC3\xA9.txt";
    CHECK(una::norm::to_nfc_utf8(nfd_name) == nfc_name);
    CHECK(nfd_name != nfc_name);   // 两个名字在字节层面确实不同，否则本用例是恒真

    const std::string payload =
        std::string("uni-algo \xE6\xB5\x8B\xE8\xAF\x95 caf\xC3\xA9 \U0001F63A\n");
    bool created = false;
    {
        std::FILE* f = std::fopen(nfd_name.c_str(), "wb");
        if (f != nullptr) {
            created = std::fwrite(payload.data(), 1, payload.size(), f) == payload.size();
            std::fclose(f);
        }
    }
    CHECK(created);
    if (created) {
        // 枚举目录，取回文件系统真正存下来的字节序列
        std::string from_fs;
        DIR* dir = opendir(".");
        if (dir != nullptr) {
            struct dirent* de = nullptr;
            while ((de = readdir(dir)) != nullptr) {
                if (std::strcmp(de->d_name, nfd_name.c_str()) == 0) {
                    from_fs = de->d_name;
                    break;
                }
            }
            closedir(dir);
        }
        // 关键平台断言：鸿蒙文件系统不改变文件名原始字节（不做 NFC/NFD 归一化）
        CHECK(from_fs == nfd_name);

        std::FILE* f = std::fopen(from_fs.c_str(), "rb");
        CHECK(f != nullptr);
        if (f != nullptr) {
            std::string read_back;
            char buf[256];
            size_t n = 0;
            while ((n = std::fread(buf, 1, sizeof(buf), f)) > 0)
                read_back.append(buf, n);
            std::fclose(f);
            CHECK(read_back == payload);
            CHECK(una::is_valid_utf8(read_back));
            // 读回的正文按 Unicode 规则处理：NFC 后长度不变（é 已是合成形式）
            const std::string nfc = una::norm::to_nfc_utf8(read_back);
            CHECK(nfc == read_back);
            CHECK(una::utf32to8(una::utf8to32u(nfc)) == nfc);
            CHECK(count_graphemes("caf\xC3\xA9") == 4);
        }
        CHECK(std::remove(nfd_name.c_str()) == 0);
    }

    // 用一个「不存在且带非法组合序列」的名字确认 fopen 不会因为编码问题而误开成功
    {
        const std::string bad = std::string("uni-algo11505-absent-") + kCjk1 +
                                "\xCC\x81\xCC\x81\xCC\x82-nonexistent.txt";
        std::FILE* f = std::fopen(bad.c_str(), "rb");
        CHECK(f == nullptr);
        if (f != nullptr)
            std::fclose(f);
    }

    // ---- 5) 大缓冲：98304 字节 / 32768 码点 ----
    {
        std::u32string big32(32768, 0x6D4B);   // 测 x 32768
        const std::string big8 = una::utf32to8(big32);
        CHECK(big8.size() == 98304);
        CHECK(una::utf8to32u(big8) == big32);
        CHECK(una::is_valid_utf8(big8));
        CHECK(una::norm::to_nfc_utf8(big8) == big8);
        CHECK(count_graphemes(big8) == 32768);
        CHECK(una::utf16to8(una::utf8to16u(big8)) == big8);
    }

    std::cout << "OHOS-SPECIAL: " << g_pass << "/" << g_total << " passed\n";
    if (g_pass != g_total)
        return 1;
    std::cout << "OHOS SPECIAL ALL CHECKS PASSED" << '\n';
    return 0;
}
