// libabw 0.1.3 消费者测试：以库使用者身份调用 libabw 公开 API，
// 解析内存中的 AbiWord(.abw) XML 文档并断言提取出的文本内容。
#include <cstdio>
#include <cstring>

#include <libabw/AbiDocument.h>
#include <librevenge/librevenge.h>
#include <librevenge-generators/librevenge-generators.h>

static const char *kAbwDocument =
    "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
    "<abiword>\n"
    "  <body>\n"
    "    <section>\n"
    "      <p style=\"Normal\">Hello HarmonyOS libabw</p>\n"
    "    </section>\n"
    "  </body>\n"
    "</abiword>\n";

static int g_failures = 0;

static void check(bool cond, const char *msg)
{
    std::printf("[%s] %s\n", cond ? "PASS" : "FAIL", msg);
    if (!cond)
        ++g_failures;
}

int main()
{
    librevenge::RVNGStringStream stream(
        reinterpret_cast<const unsigned char *>(kAbwDocument),
        static_cast<unsigned int>(std::strlen(kAbwDocument)));

    check(libabw::AbiDocument::isFileFormatSupported(&stream),
          "isFileFormatSupported(.abw XML) == true");

    librevenge::RVNGString text;
    librevenge::RVNGTextTextGenerator generator(text, /*isInfo=*/false);
    const bool parsed = libabw::AbiDocument::parse(&stream, &generator);
    check(parsed, "parse(.abw XML) == true");

    if (parsed)
        check(std::strstr(text.cstr(), "Hello HarmonyOS libabw") != nullptr,
              "extracted text contains payload string");
    else
        check(false, "extracted text contains payload string (parse failed)");

    std::printf("checks=3 failures=%d\n", g_failures);
    return g_failures == 0 ? 0 : 1;
}
