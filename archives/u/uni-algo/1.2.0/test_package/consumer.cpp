/* uni-algo 1.2.0 消费者验证用例
 *
 * 只用公开头文件 <uni_algo/all.h> 与公开 API，链接包内 libuni-algo.a 并实际运行：
 * 编译期依赖 include/，链接期依赖 lib/（所有 Unicode 数据表都在静态库里，
 * 头文件的 inline 实现必须引用它们），任一目录缺失都会在 L1e 反向验证里变红。
 *
 * 全部非 ASCII 一律写成 \x / \u 转义或用整型常量表示码点，源码文件本身只含 ASCII，
 * 避免字节在 git / base64 上传链路上被改写；期望值取自上游 README 与 test/ 的原文。
 */
#include <iostream>
#include <string>
#include <vector>

#include <uni_algo/all.h>
#include <uni_algo/locale.h>

static int g_total = 0;
static int g_pass = 0;

// 变参形式：断言表达式里带 `{1, 2, 0}` 这类初始化列表时逗号会被当成宏参数分隔符
#define CHECK(...)                                                                 \
    do {                                                                           \
        ++g_total;                                                                 \
        if (__VA_ARGS__) { ++g_pass; }                                             \
        else { std::cout << "CHECK FAILED: " #__VA_ARGS__ " @line " << __LINE__ << '\n'; } \
    } while (0)

// 编译期就要求版本对得上（拿到别的版本整包就是错的）
static_assert(una::version::library == una::version::library_v{1, 2, 0},
              "packaged uni-algo is not 1.2.0");

static int count_graphemes(const std::string& s)
{
    int n = 0;
    auto view = una::ranges::grapheme::utf8_view{s};
    for (auto it = view.begin(); it != view.end(); ++it)
        ++n;
    return n;
}

static int count_words(const std::string& s)
{
    int n = 0;
    auto view = una::ranges::word::utf8_view{s};
    for (auto it = view.begin(); it != view.end(); ++it)
        ++n;
    return n;
}

static int count_words_only(const std::string& s)
{
    int n = 0;
    auto view = una::ranges::word_only::utf8_view{s};
    for (auto it = view.begin(); it != view.end(); ++it)
        ++n;
    return n;
}

// 逐段取回文本（代理迭代器给的是段首/段尾迭代器，不是指针）
static std::vector<std::string> segments(const std::string& s)
{
    std::vector<std::string> out;
    auto view = una::ranges::word::utf8_view{s};
    for (auto it = view.begin(); it != view.end(); ++it)
        out.emplace_back(it.begin(), it.end());
    return out;
}

int main()
{
    std::cout << "uni-algo consumer probe (linked against packaged libuni-algo.a)\n";

    // 常用码点/串（全部用整型码点或 UTF-8 字节转义给出）
    const char32_t cp_A     = 'W';
    const char32_t cp_w     = 'w';
    const char32_t cp_7     = '7';
    const char32_t cp_acute = 0x0301;   // COMBINING ACUTE ACCENT
    const char32_t cp_sur   = 0xD800;   // 未配对高代理
    const char32_t cp_cjk   = 0x6D4B;   // 测
    const std::string cyr_up   = "\xD0\x94\xD0\x92\xD0\x90";  // ДВА
    const std::string cyr_low  = "\xD0\xB4\xD0\xB2\xD0\xB0";  // два
    const std::string ukr_a    = "\xD0\xB0";                  // а
    const std::string ukr_A    = "\xD0\x90";                  // А
    const std::string emoji3   = "\U0001F63A\U0001F63C\U0001F640";
    const std::string ohm      = "\xCE\xA9";                  // Ω GREEK CAPITAL LETTER OMEGA

    // ---- 版本 ----
    CHECK(una::version::library == una::version::library_v{1, 2, 0});
    CHECK(una::version::unicode == una::version::unicode_v{15, 1, 0});

    // ---- 宽松转换：未配对代理 -> U+FFFD，截断序列 -> U+FFFD ----
    CHECK(una::utf16to8(u"Te\xD800st") == "Te\xEF\xBF\xBDst");
    CHECK(una::utf8to16u("Te\xC2st") == u"Te\xFFFDst");

    // ---- UTF-8 <-> UTF-32 往返（补充平面） ----
    const std::u32string emoji32 = una::utf8to32u(emoji3);
    CHECK(emoji32 == U"\U0001F63A\U0001F63C\U0001F640");
    CHECK(una::utf32to8(emoji32) == emoji3);
    CHECK(emoji32.size() == 3);

    // ---- UTF-8 -> UTF-16 -> UTF-8 往返（西里尔，BMP） ----
    CHECK(una::utf16to8(una::utf8to16u(cyr_up)) == cyr_up);

    // ---- 严格转换必须失败并给出错误位置 ----
    una::error err_strict;
    const std::u16string strict = una::strict::utf8to16u("Te\xC2st", err_strict);
    CHECK(strict.empty());
    CHECK(static_cast<bool>(err_strict));
    CHECK(err_strict.pos() == 2);

    // ---- UTF-8 合法性判定 ----
    CHECK(una::is_valid_utf8(cyr_up));
    CHECK(una::is_valid_utf8("\xEF\xBC\xA1\xEF\xBC\xA2\xEF\xBC\xA3"));
    CHECK(una::is_valid_utf8("\xF0\x9D\x90\x80\xF0\x9D\x90\x81\xF0\x9D\x90\x82"));
    CHECK(una::utf32to8(una::utf8to32u(ohm)) == ohm);

    // ---- 大小写映射（一对一膨胀 / 折叠 / 标题式） ----
    // ß 后面的 e 必须断开，否则 \x9Fe 会被当成一个越界的十六进制转义
    CHECK(una::cases::to_uppercase_utf8("stra\xC3\x9F" "e") == "STRASSE");
    CHECK(una::cases::to_lowercase_utf8(cyr_up) == cyr_low);
    CHECK(una::cases::to_casefold_utf8("Ligature \xEF\xAC\x83") == "ligature ffi");
    CHECK(una::cases::to_titlecase_utf8("teMPuS eDAX reRuM") == "Tempus Edax Rerum");

    // ---- 带 locale 的大小写映射（土耳其 / 希腊 / 荷兰） ----
    CHECK(una::cases::to_uppercase_utf8("istanbul", una::locale{"tr"}) ==
          "\xC4\xB0STANBUL");
    CHECK(una::cases::to_uppercase_utf8(
              "\xE1\xBC\x88\xCF\x81\xCE\xB9\xCF\x83\xCF\x84\xCE\xBF"
              "\xCF\x84\xCE\xAD\xCE\xBB\xCE\xB7\xCF\x82",
              una::locale{"el"}) ==
          "\xCE\x91\xCE\xA1\xCE\x99\xCE\xA3\xCE\xA4\xCE\x9F\xCE\xA4\xCE\x95"
          "\xCE\x9B\xCE\x97\xCE\xA3");
    CHECK(una::cases::to_titlecase_utf8("ijsland", una::locale{"nl"}) == "IJsland");

    // ---- 忽略大小写的比较与查找 ----
    CHECK(una::caseless::compare_utf8("\xEF\xAC\x83", "FFI") == 0);
    const una::found found = una::caseless::find_utf8("Ligature \xEF\xAC\x81 test", "FI");
    CHECK(static_cast<bool>(found));
    CHECK(found.pos() == 9);
    CHECK(found.end_pos() == 12);

    // ---- 有案 / 忽略案匹配排序：与二进制序相反，说明真的走了 Unicode 数据表 ----
    CHECK(una::casesens::collate_utf8(ukr_a, ukr_A) < 0);
    CHECK(ukr_a > ukr_A);
    CHECK(una::caseless::collate_utf8(ukr_a, ukr_A) == 0);

    // ---- 归一化 NFC / NFD / NFKC / NFKD ----
    CHECK(una::norm::to_nfc_utf8("W\xCC\x82") == "\xC5\xB4");
    CHECK(una::norm::is_nfc_utf8("\xC5\xB4"));
    CHECK(!una::norm::is_nfc_utf8("W\xCC\x82"));
    CHECK(una::norm::to_nfd_utf8("\xC5\xB4") == "W\xCC\x82");
    CHECK(una::norm::is_nfd_utf8("W\xCC\x82"));
    CHECK(!una::norm::is_nfd_utf8("\xC5\xB4"));
    CHECK(una::norm::to_nfkc_utf8("\xEF\xAC\x81") == "fi");
    CHECK(una::norm::to_nfkd_utf8("\xEF\xAC\x81") == "fi");
    CHECK(una::norm::to_nfc_utf8("\xC5\xB4") == "\xC5\xB4");

    // ---- 码点属性 ----
    CHECK(una::codepoint::is_numeric(cp_7));
    CHECK(una::codepoint::is_alphabetic(cp_A));
    CHECK(una::codepoint::is_lowercase(cp_w));
    CHECK(una::codepoint::prop{cp_A}.Alphabetic());
    CHECK(una::codepoint::prop{cp_acute}.General_Category_M());
    CHECK(una::codepoint::is_surrogate(cp_sur));
    CHECK(!una::codepoint::is_surrogate(cp_A));

    // ---- Script 检测 ----
    CHECK(una::codepoint::get_script(cp_cjk) == una::locale::script{"Hani"});
    CHECK(una::codepoint::get_script(cp_sur) == una::locale::script{"Zzzz"});

    // ---- Locale 解析与子标签 ----
    const una::locale loc{"EN_latn_US"};
    CHECK(loc.to_string() == "en-Latn-US");
    CHECK(loc == una::locale::language{"en"});
    CHECK(loc == una::locale::region{"US"});
    CHECK(!loc.is_empty());
    CHECK(loc.get_language() == una::locale::language{"en"});

    // ---- 范围视图：逐码点反转 + 截取（罗马数字 Ⅰ..Ⅹ -> Ⅲ..Ⅶ） ----
    const std::string roman = "\xE2\x85\xA0\xE2\x85\xA1\xE2\x85\xA2\xE2\x85\xA3\xE2\x85\xA4"
                              "\xE2\x85\xA5\xE2\x85\xA6\xE2\x85\xA7\xE2\x85\xA8\xE2\x85\xA9";
    const std::string expect_mid = "\xE2\x85\xA2\xE2\x85\xA3\xE2\x85\xA4\xE2\x85\xA5\xE2\x85\xA6";
    const std::string slice =
        std::string_view{roman} | una::views::utf8 | una::views::reverse |
        una::views::drop(3) | una::views::take(5) | una::views::reverse |
        una::ranges::to_utf8<std::string>();
    CHECK(slice == expect_mid);
    CHECK(count_graphemes(roman) == 10);

    // ---- 字素簇与词断句（UAX #29 默认算法） ----
    CHECK(count_graphemes("a\xCC\x81") == 1);   // a + 组合尖音符 = 1 个字素簇
    CHECK(count_graphemes("\U0001F468\xE2\x80\x8D\U0001F469\xE2\x80\x8D"
                          "\U0001F467\xE2\x80\x8D\U0001F466") == 1);   // ZWJ 家庭 emoji
    // word 迭代器按默认算法逐段切（标点与空白各自成段），word_only 才只要词
    CHECK(count_words("Hello, world!") == 5);
    CHECK(count_words_only("Hello, world!") == 2);
    const std::vector<std::string> segs = segments("Hello, world!");
    CHECK(segs.size() == 5);
    CHECK(segs[0] == "Hello" && segs[1] == "," && segs[2] == " ");
    CHECK(segs[3] == "world" && segs[4] == "!");

    std::cout << "CONSUMER: " << g_pass << "/" << g_total << " passed\n";
    if (g_pass != g_total)
        return 1;
    std::cout << "CONSUMER ALL CHECKS PASSED" << '\n';
    return 0;
}
