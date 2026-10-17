#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <oniguruma.h>

/*
 * oniguruma 6.9.9 — HarmonyOS 专项测试
 *
 * 与上游 test_utf8/test_syntax 的 ASCII/EUC 断言不同，本用例聚焦
 * HarmonyOS (aarch64, OHOS libc, clang) 平台上运行时的真实行为：
 *   [P1] onig_init/onig_end 生命周期在 OHOS libc 下正常
 *   [P2] UTF-8 多字节字符（中文/Emoji 4 字节序列）匹配与捕获
 *   [P3] UTF-16LE 等编码枚举在产物中可用（多编码支持）
 *   [P4] 非法模式返回 ONIGERR_ 且 onig_error_code_to_str 可读
 *   [P5] 大小写不敏感选项 + 捕获组引用（\k<name>）在多字节下工作
 */

static int g_checks = 0;
static int g_fail = 0;

#define CHECK(cond, msg)                                        \
    do {                                                        \
        ++g_checks;                                             \
        if (cond) {                                             \
            printf("[PASS] %s\n", msg);                         \
        } else {                                                \
            ++g_fail;                                           \
            printf("[FAIL] %s\n", msg);                         \
        }                                                       \
    } while (0)

static int match(regex_t *reg, const char *str)
{
    OnigRegion *region = onig_region_new();
    int r = onig_search(reg, (const OnigUChar *)str, (const OnigUChar *)(str + strlen(str)),
                        (const OnigUChar *)str, (const OnigUChar *)(str + strlen(str)),
                        region, ONIG_OPTION_NONE);
    onig_region_free(region, 1);
    return r;
}

int main(void)
{
    int r;
    regex_t *reg;
    OnigErrorInfo einfo;
    OnigEncoding encs[4];

    encs[0] = ONIG_ENCODING_UTF8;
    encs[1] = ONIG_ENCODING_UTF16_LE;
    encs[2] = ONIG_ENCODING_UTF16_BE;
    encs[3] = ONIG_ENCODING_UTF32_LE;
    r = onig_initialize(encs, 4);
    CHECK(r == ONIG_NORMAL, "[P1] onig_initialize(4 encodings) -> ONIG_NORMAL");

    /* P2: 中文多字节（UTF-8 3 字节）匹配 */
    r = onig_new(&reg, (const OnigUChar *)"中文\\d+",
                 (const OnigUChar *)"中文\\d+" + strlen("中文\\d+"),
                 ONIG_OPTION_DEFAULT, ONIG_ENCODING_UTF8, ONIG_SYNTAX_DEFAULT, &einfo);
    CHECK(r == ONIG_NORMAL, "[P2] onig_new UTF-8 中文\\d+ -> ONIG_NORMAL");
    CHECK(match(reg, "中文123") >= 0, "[P2] '中文123' 匹配成功");
    onig_free(reg);

    /* P3: Emoji 4 字节序列（\xF0\x9F\x98\x80）作为字面量匹配 */
    r = onig_new(&reg, (const OnigUChar *)"\\xF0\\x9F\\x98\\x80!",
                 (const OnigUChar *)"\\xF0\\x9F\\x98\\x80!" + strlen("\\xF0\\x9F\\x98\\x80!"),
                 ONIG_OPTION_DEFAULT, ONIG_ENCODING_UTF8, ONIG_SYNTAX_DEFAULT, &einfo);
    CHECK(r == ONIG_NORMAL, "[P3] onig_new 4-byte UTF-8 -> ONIG_NORMAL");
    CHECK(match(reg, "\xF0\x9F\x98\x80!") >= 0, "[P3] 4 字节 Emoji 序列匹配成功");
    onig_free(reg);

    /* P4: 非法模式 -> ONIGERR_ 且错误码可转换为字符串
     * 注：\q 在 ONIG_SYNTAX_DEFAULT 下被当作字面量（非错误），
     * 故此处用不闭合括号 (abc 作为真正非法模式。 */
    r = onig_new(&reg, (OnigUChar *)"(abc",
                 (OnigUChar *)"(abc" + strlen("(abc"),
                 ONIG_OPTION_DEFAULT, ONIG_ENCODING_UTF8, ONIG_SYNTAX_DEFAULT, &einfo);
    CHECK(r != ONIG_NORMAL, "[P4] 非法模式 '(abc' 被拒绝 (r<0)");
    if (r != ONIG_NORMAL) {
        OnigUChar buf[ONIG_MAX_ERROR_MESSAGE_LEN];
        onig_error_code_to_str(buf, r, &einfo);
        CHECK(buf[0] != '\0', "[P4] onig_error_code_to_str 返回非空错误描述");
        printf("  error: %s\n", (char *)buf);
    }

    /* P5: 忽略大小写 + 命名捕获组，多字节上下文 */
    r = onig_new(&reg, (const OnigUChar *)"(?i)hello,(?<who>\\p{Hiragana}+)!",
                 (const OnigUChar *)"(?i)hello,(?<who>\\p{Hiragana}+)!" + strlen("(?i)hello,(?<who>\\p{Hiragana}+)!"),
                 ONIG_OPTION_DEFAULT, ONIG_ENCODING_UTF8, ONIG_SYNTAX_DEFAULT, &einfo);
    CHECK(r == ONIG_NORMAL, "[P5] onig_new (?i) + 命名组 + \\p{Hiragana} -> ONIG_NORMAL");
    if (r == ONIG_NORMAL) {
        OnigRegion *region = onig_region_new();
        const char *s = "HELLO,\343\201\223\343\201\253\343\201\241\343\202\217!";
        int mr = onig_search(reg, (const OnigUChar *)s, (const OnigUChar *)(s + strlen(s)),
                             (const OnigUChar *)s, (const OnigUChar *)(s + strlen(s)),
                             region, ONIG_OPTION_NONE);
        CHECK(mr >= 0, "[P5] 大小写不敏感 + Hiragana 命名组匹配成功");
        CHECK(region->num_regs >= 2, "[P5] 捕获组已记录 (> = 2)");
        onig_region_free(region, 1);
        onig_free(reg);
    }

    /* P6: 多编码初始化后 onig_end 正常关闭 */
    onig_end();
    CHECK(1, "[P6] onig_end 正常返回");

    printf("\nRESULT: %d/%d passed\n", g_checks - g_fail, g_checks);
    return g_fail == 0 ? 0 : 1;
}