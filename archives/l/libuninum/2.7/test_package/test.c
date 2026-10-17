/* Consumer test for libuninum 2.7 — exercises the core string<->number API.
 *
 * 测试向量取自上游 TestFiles/TestStringToNumber.tcl（探索性打印脚本，
 * 无自动断言）；断言行为均在 OHOS 真机实测确认。注意：
 * - UTF32 是 unsigned long（aarch64 上 8 字节），与 OHOS 4 字节 wchar_t
 *   不同，必须手工构造 UTF32 数组，不能直接传 L"" 字面量。
 * - 西方数字属于带进制参数的 Western_General 系统，GuessNumberSystem
 *   对其返回 NS_UNKNOWN，StringToInt 需显式指定 NS_WESTERN。
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <gmp.h>
#include <uninum/unicode.h>
#include <uninum/nsdefs.h>
#include <uninum/uninum.h>

static int g_assertions = 0;

#define ASSERT(cond, msg)                                              \
    do {                                                               \
        g_assertions++;                                                \
        if (!(cond)) {                                                 \
            fprintf(stderr, "FAIL line %d: %s\n", __LINE__, (msg));   \
            exit(1);                                                   \
        }                                                              \
    } while (0)

static UTF32 western[] = {0x0032, 0x0038, 0x0033, 0x0037, 0x0035, 0x0000}; /* "28375" */
static UTF32 arabic[] = {0x0666, 0x0664, 0x0665, 0x0663, 0x0000};          /* U+0666 U+0664 U+0665 U+0663 */
static UTF32 devanagari[] = {0x096A, 0x096B, 0x0969, 0x0000};              /* 4 5 3 */
static UTF32 badchar[] = {0x1F600, 0x0000};                                /* emoji */

int main(void)
{
    union ns_rval val;
    UTF32 *out;

    /* ---- 版本 ---- */
    char *ver = uninum_version();
    ASSERT(ver != NULL, "uninum_version() returned NULL");
    ASSERT(strcmp(ver, "2.7") == 0, "uninum_version() != 2.7");

    /* ---- 西方数字 "28375"（上游 Tcl 测试向量；需显式指定 Western 系统）---- */
    StringToInt(&val, western, NS_TYPE_ULONG, NS_WESTERN);
    ASSERT(uninum_err == NS_ERROR_OKAY, "StringToInt(western/NS_WESTERN) set error");
    ASSERT(val.u == 28375, "StringToInt(western) != 28375");
    /* 猜测系统不含西方数字（进制未定），确定性返回 NS_UNKNOWN */
    StringToInt(&val, western, NS_TYPE_ULONG, NS_ANY);
    ASSERT(uninum_err == NS_ERROR_UNKNOWN, "StringToInt(western/NS_ANY) not NS_ERROR_UNKNOWN");
    ASSERT(GuessNumberSystem(western) == NS_UNKNOWN, "GuessNumberSystem(western) != NS_UNKNOWN");

    /* ---- 阿拉伯-印度数字 6453（上游 Tcl 测试向量）---- */
    StringToInt(&val, arabic, NS_TYPE_ULONG, NS_ANY);
    ASSERT(uninum_err == NS_ERROR_OKAY, "StringToInt(arabic/NS_ANY) set error");
    ASSERT(val.u == 6453, "StringToInt(arabic) != 6453");
    StringToInt(&val, arabic, NS_TYPE_ULONG, NS_ARABIC_WESTERN);
    ASSERT(uninum_err == NS_ERROR_OKAY && val.u == 6453,
           "StringToInt(arabic/NS_ARABIC_WESTERN) failed");

    /* ---- 天城文数字 453（上游 Tcl 测试向量）---- */
    StringToInt(&val, devanagari, NS_TYPE_ULONG, NS_ANY);
    ASSERT(uninum_err == NS_ERROR_OKAY, "StringToInt(devanagari) set error");
    ASSERT(val.u == 453, "StringToInt(devanagari) != 453");

    /* ---- 数字系统猜测 ---- */
    ASSERT(GuessNumberSystem(arabic) == NS_ARABIC_WESTERN,
           "GuessNumberSystem(arabic) != NS_ARABIC_WESTERN");
    ASSERT(GuessNumberSystem(devanagari) == NS_DEVANAGARI,
           "GuessNumberSystem(devanagari) != NS_DEVANAGARI");

    /* ---- 数字系统名称双向映射 ---- */
    ASSERT(StringToNumberSystem("Arabic_Western") == NS_ARABIC_WESTERN,
           "StringToNumberSystem(\"Arabic_Western\") failed");
    char *devname = NumberSystemToString(NS_DEVANAGARI);
    ASSERT(devname != NULL && strcmp(devname, "Devanagari") == 0,
           "NumberSystemToString(NS_DEVANAGARI) != \"Devanagari\"");

    /* ---- IntToString -> StringToInt 往返（阿拉伯-印度数字）---- */
    val.u = 123456789;
    out = IntToString(&val, NS_ARABIC_WESTERN, NS_TYPE_ULONG);
    ASSERT(out != NULL, "IntToString returned NULL");
    StringToInt(&val, out, NS_TYPE_ULONG, NS_ARABIC_WESTERN);
    free(out);
    ASSERT(uninum_err == NS_ERROR_OKAY, "round-trip StringToInt set error");
    ASSERT(val.u == 123456789, "round-trip value != 123456789");

    /* ---- 非法字符报错（uninum.c 中 default 分支 -> BADCHARACTER）---- */
    StringToInt(&val, badchar, NS_TYPE_ULONG, NS_ARABIC_WESTERN);
    ASSERT(uninum_err == NS_ERROR_BADCHARACTER,
           "bad character not reported as NS_ERROR_BADCHARACTER");

    printf("libuninum test_package: %d assertions passed\n", g_assertions);
    return 0;
}
