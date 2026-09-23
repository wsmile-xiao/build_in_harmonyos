/* test_pcre32.c — 消费者视角验证 libpcre32 公开 API：
 * pcre32_compile / pcre32_exec / pcre32_free 编译执行 roundtrip。
 * pcre32 输入为 PCRE_UCHAR32（unsigned int）码元数组，须显式转换。
 * 断言口径见 MANIFEST.yml。
 */
#include <stdio.h>
#include <string.h>
#include <pcre.h>

#define CHECK(cond) do { \
    if (!(cond)) { \
        fprintf(stderr, "FAIL: %s (line %d)\n", #cond, __LINE__); \
        return 1; \
    } \
} while (0)

static void ascii_to_uchar32(const char *src, PCRE_UCHAR32 *dst)
{
    size_t i;
    for (i = 0; src[i] != '\0'; i++)
        dst[i] = (PCRE_UCHAR32)(unsigned char)src[i];
    dst[i] = 0;
}

int main(void)
{
    PCRE_UCHAR32 pattern_buf[16];
    PCRE_UCHAR32 subject_buf[16];
    const char *errptr;
    int erroffset;
    int ovector[6];
    int rc;

    ascii_to_uchar32("a.c+", pattern_buf);
    ascii_to_uchar32("abcccxyz", subject_buf);

    /* 1. pcre32_compile：编译 32 位模式 */
    pcre32 *re = pcre32_compile(
        pattern_buf, 0, &errptr, &erroffset, NULL);
    CHECK(re != NULL);

    /* 2. pcre32_exec：匹配 subject */
    rc = pcre32_exec(re, NULL, subject_buf, 8, 0, 0, ovector, 6);
    CHECK(rc >= 1);

    /* 3. 匹配到的子串长度与模式预期一致（"abccc" 5 字符） */
    CHECK(ovector[1] - ovector[0] == 5);

    /* 4. 无匹配返回 0/负值（不误报） */
    ascii_to_uchar32("zzz", subject_buf);
    rc = pcre32_exec(re, NULL, subject_buf, 3, 0, 0, ovector, 6);
    CHECK(rc != 1);

    pcre32_free(re);
    printf("test_pcre32: OK (compile+exec roundtrip)\n");
    return 0;
}
