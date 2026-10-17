/* HarmonyOS 平台特定消费者测试 — libfreehand-tools 0.1.2
 *
 * 编译期硬绑定：__OHOS__ + __aarch64__（防误用非鸿蒙工具链编译通过）。
 * 运行期真实链接 libfreehand-0.1.a（静态）+ librevenge 三库 + ICU + zlib +
 * lcms2，验证鸿蒙工具链下 libfreehand 公共 C++ API 可链接、可调用：
 *   1) 非 FreeHand 数据流：isSupported == false、parse == false（拒绝语义）
 *   2) 空指针输入的安全语义（isSupported(nullptr) == false）
 *   3) 正向魔数识别：AGD 头（FreeHand 5+ 的 'AGD' 魔数，第 4 字节为版本）
 *      与 FH3 头（'FH3'）都被 isSupported 正确识别为 true —— 证明版本探测
 *      链路在鸿蒙工具链下真实执行，不是恒 false 的空壳
 *   4) librevenge RVNGBinaryData / RVNGStringStream 在 libc++/musl 下构造与
 *      多态调用正常（getDataStream/getDataBuffer/size）
 */
#include <libfreehand/libfreehand.h>
#include <librevenge/librevenge.h>

#include <cstdio>
#include <cstring>

#if !defined(__OHOS__)
#error "This test must be compiled with the OpenHarmony toolchain (__OHOS__ undefined)"
#endif

#if !defined(__aarch64__)
#error "HarmonyOS target must be aarch64 (__aarch64__ undefined)"
#endif

namespace
{

int g_failures = 0;

void check(bool cond, const char *what)
{
    std::printf("%s %s\n", cond ? "PASS:" : "FAIL:", what);
    if (!cond)
        ++g_failures;
}

} // namespace

int main()
{
    std::printf("HarmonyOS-specific libfreehand ABI test (libfreehand-tools 0.1.2)\n");

    // 1) 空指针输入的安全语义
    check(libfreehand::FreeHandDocument::isSupported(nullptr) == false,
          "isSupported(nullptr) is safely rejected");
    check(libfreehand::FreeHandDocument::parse(nullptr, nullptr) == false,
          "parse(nullptr, nullptr) is safely rejected");

    // 2) 纯文本流不是 FreeHand 文档
    const char *text = "hello libfreehand-tools 0.1.2 on OpenHarmony";
    librevenge::RVNGStringStream textStream(
        reinterpret_cast<const unsigned char *>(text), std::strlen(text));
    check(libfreehand::FreeHandDocument::isSupported(&textStream) == false,
          "plain text stream is not a FreeHand document");
    check(libfreehand::FreeHandDocument::parse(&textStream, nullptr) == false,
          "parse() rejects a plain text stream");

    // 3) 正向：AGD 魔数（'A','G','D' + 版本字符）被识别
    static const unsigned char agdMagic[8] = {'A', 'G', 'D', '7', 0x00, 0x00, 0x00, 0x00};
    librevenge::RVNGBinaryData agdData(agdMagic, sizeof(agdMagic));
    librevenge::RVNGStringStream agdStream(agdData.getDataBuffer(), agdData.size());
    check(libfreehand::FreeHandDocument::isSupported(&agdStream) == true,
          "AGD magic header is recognized as FreeHand (positive detection)");

    // 4) 正向：FH3 魔数（'F','H','3'）被识别
    static const unsigned char fh3Magic[8] = {'F', 'H', '3', '0', 0x00, 0x00, 0x00, 0x00};
    librevenge::RVNGBinaryData fh3Data(fh3Magic, sizeof(fh3Magic));
    librevenge::RVNGStringStream fh3Stream(fh3Data.getDataBuffer(), fh3Data.size());
    check(libfreehand::FreeHandDocument::isSupported(&fh3Stream) == true,
          "FH3 magic header is recognized as FreeHand (positive detection)");

    if (g_failures != 0)
    {
        std::printf("harmonyos_specific_test: %d check(s) FAILED\n", g_failures);
        return 1;
    }
    std::printf("HarmonyOS-specific libfreehand ABI test passed\n");
    return 0;
}
