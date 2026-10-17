// HarmonyOS 专项测试 — tiny-utf8 4.4.3
//
// 本用例为鸿蒙 PC (OHOS aarch64, clang-15 armv8) 工具链专项验证, 与上游
// gtest 用例互补: 上游覆盖库通用功能, 本用例聚焦 OHOS 平台文本处理场景
// (中文 CJK、Emoji 四字节码点、码点边界 U+10FFFF、混合脚本), 并验证
// tiny_utf8::string 在 OHOS 工具链下按码点而非字节正确工作。
//
// 构建/运行: 随 test_package 由 conan create (profile: ohos-aarch64) 编译
// 并在目标环境执行, 由 CTest 注册为独立用例 test_tiny-utf8-ohos。
// NOTE: 使用显式检查 (非 assert), 确保 Release/NDEBUG 下断言仍生效。
#include <cstdio>
#include <string>

#include <tinyutf8/tinyutf8.h>

#define TINYUTF8_CHECK(cond)                                                     \
    do {                                                                         \
        if (!(cond)) {                                                           \
            std::fprintf(stderr, "FAIL %s:%d: %s\n", __FILE__, __LINE__, #cond); \
            return 1;                                                            \
        }                                                                        \
    } while (0)

int main(void) {
    // 1) CJK 中文文本: 码点长度与字节长度必须区分 (UTF-8 每汉字 3 字节)。
    tiny_utf8::string cn(u8"鸿蒙操作系统");
    TINYUTF8_CHECK(cn.length() == 6);            // 6 个汉字
    TINYUTF8_CHECK(cn.size() == 18);             // 6 * 3 字节
    TINYUTF8_CHECK(cn[0] == U'鸿');
    TINYUTF8_CHECK(cn[5] == U'统');

    // 2) Emoji: 四字节 UTF-8 码点 (U+1F600..U+1F64F 区段)。
    tiny_utf8::string emoji(u8"😀😁😂");
    TINYUTF8_CHECK(emoji.length() == 3);         // 3 个码点
    TINYUTF8_CHECK(emoji.size() == 12);          // 3 * 4 字节
    TINYUTF8_CHECK(emoji[1] == U'😁');

    // 3) 码点边界: 最大合法码点 U+10FFFF (4 字节 UTF-8: F4 8F BF BF)。
    tiny_utf8::string maxcp;
    maxcp.push_back(U'\U0010FFFF');
    TINYUTF8_CHECK(maxcp.length() == 1);
    TINYUTF8_CHECK(maxcp.size() == 4);

    // 4) 混合脚本 (ASCII + 中文 + emoji): 迭代顺序与码点索引一致。
    tiny_utf8::string mixed(u8"OH-鸿蒙-😀");
    TINYUTF8_CHECK(mixed.length() == 7);         // 'O','H','-',鸿,蒙,'-',😀
    TINYUTF8_CHECK(mixed[0] == U'O');
    TINYUTF8_CHECK(mixed[3] == U'鸿');
    TINYUTF8_CHECK(mixed[6] == U'😀');
    TINYUTF8_CHECK(mixed.find(u8"鸿蒙") == 3);

    // 5) 子串操作按码点边界, 不会从多字节序列中间切开。
    tiny_utf8::string sub = cn.substr(2, 2);
    TINYUTF8_CHECK(sub == u8"操作");

    std::printf("test_tiny-utf8-ohos: HarmonyOS UTF-8 专项验证通过 "
                "(CJK=%zuB/%zucp, emoji=%zuB/%zucp, maxcp=%zuB, mixed=%zuB/%zucp)\n",
                static_cast<size_t>(cn.size()), static_cast<size_t>(cn.length()),
                static_cast<size_t>(emoji.size()), static_cast<size_t>(emoji.length()),
                static_cast<size_t>(maxcp.size()),
                static_cast<size_t>(mixed.size()), static_cast<size_t>(mixed.length()));
    return 0;
}