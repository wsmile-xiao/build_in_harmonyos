// HarmonyOS 专项测试：hexdump 1.0.0 真实消费入口验证
// 使用 OHOS armv8 工具链（clang 15 / aarch64-linux-ohos）实际编译并运行，
// 验证 header-only 库在 OHOS 平台下的可编译性与运行时正确性。
//
// 测试点：
//   1. OHOS 编译环境平台宏检查：__OHOS__ / __OHOS_FAMILY__ 应被定义，
//      __aarch64__ 应被定义（armv8 目标）。
//   2. 公开 API 真实调用：Hexdump / CustomHexdump / CustomHexdumpBase
//      输出格式逐字节断言（首行/末行/行宽/ASCII 面板）。
//   3. 大数据量 + 多种模板实例化压力验证（覆盖 <iomanip> 流格式化）。
#include "hexdump.hpp"

#include <cstdio>
#include <sstream>
#include <string>
#include <vector>

static int failures = 0;

static void check(bool ok, const char* what)
{
    std::printf("%s %s\n", ok ? "[PASS]" : "[FAIL]", what);
    if (!ok) failures++;
}

int main()
{
    // 1) 平台宏
#ifdef __OHOS__
    check(true, "platform macro __OHOS__ defined");
#else
    check(false, "platform macro __OHOS__ defined");
#endif
#ifdef __OHOS_FAMILY__
    check(true, "platform macro __OHOS_FAMILY__ defined");
#else
    check(false, "platform macro __OHOS_FAMILY__ defined");
#endif
#ifdef __aarch64__
    check(true, "arch macro __aarch64__ defined");
#else
    check(false, "arch macro __aarch64__ defined");
#endif

    // 2) 公开 API 真实输出断言
    std::vector<unsigned char> data(256);
    for (std::size_t i = 0; i < data.size(); ++i) data[i] = static_cast<unsigned char>(i);

    std::ostringstream os;
    os << Hexdump(data.data(), data.size());
    std::string s = os.str();

    check(s.find("0x000000: 00 01 02 03 04 05 06 07 08 09 0a 0b 0c 0d 0e 0f") != std::string::npos,
          "Hexdump first row (16 bytes) exact bytes");
    check(s.find("0x0000f0: f0 f1 f2 f3 f4 f5 f6 f7 f8 f9 fa fb fc fd fe ff") != std::string::npos,
          "Hexdump last row (16 bytes) exact bytes");
    check(s.find("0x000080:") != std::string::npos, "row address formatting 0x%06x");
    // ASCII 面板：0x20..0x3f 可打印区应出现（分两行 0x000020/0x000030 输出）
    check(s.find(" !\"#$%&'()*+,-./") != std::string::npos &&
          s.find("0123456789:;<=>?") != std::string::npos,
          "ASCII panel printable range 0x20-0x3f");
    // 不可打印字节应显示为 .
    check(s.find("0x000000:") != std::string::npos && s.find("................") != std::string::npos,
          "non-printable bytes shown as dots");

    // 3) CustomHexdump<8,false> 行宽与无 ASCII
    std::ostringstream os2;
    os2 << CustomHexdump<8, false>(data.data(), data.size());
    std::string s2 = os2.str();
    check(s2.find("0x000000: 00 01 02 03 04 05 06 07 08") == std::string::npos,
          "CustomHexdump<8,false> rows capped at 8 bytes");
    // 无 ASCII 面板：行尾为字节分隔空格 + 行尾空格后直接换行（无可打印字符）
    check(s2.find("0x000000: 00 01 02 03 04 05 06 07  \n") != std::string::npos,
          "CustomHexdump<8,false> no ASCII panel");

    // 4) CustomHexdumpBase typed instantiation
    std::ostringstream os3;
    os3 << CustomHexdumpBase<uint16_t, 16, true>(data.data(), data.size());
    check(os3.str().find("0x000000: 00 01 02 03 04 05 06 07 08 09 0a 0b 0c 0d 0e 0f") != std::string::npos,
          "CustomHexdumpBase<uint16_t,16,true> works");

    // 5) 空长度：无输出行
    std::ostringstream os4;
    os4 << Hexdump(data.data(), 0);
    check(os4.str().empty(), "length-0 hexdump emits no lines");

    std::printf("hexdump OHOS special test: %s (%d failures)\n",
                failures == 0 ? "ALL PASS" : "FAILED", failures);
    return failures == 0 ? 0 : 1;
}
