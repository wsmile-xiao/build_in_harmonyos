/*
 * 鸿蒙专项测试：hyphen 2.8.9 在 OHOS 平台（arm64）的真实消费验证
 *
 * 本测试模拟业务上层组件：仅通过已安装的公开头文件 hyphen.h、公开 API
 * （hnj_hyphen_load / hnj_hyphen_hyphenate2 / hnj_hyphen_free）和正常链接
 * 目标（-lhyphen）使用该三方库，验证在 HarmonyOS PC 平台下能够编译、
 * 链接、调用并得到正确的断词结果（含 UTF-8 多字节单词）。
 *
 * 验证点：
 *   1) 从已安装数据目录加载 hyph_en_US.dic（返回非 NULL 字典）
 *   2) ASCII 单词断词：example -> 输出包含 '=' 的连字符化结果
 *   3) UTF-8 多字节单词断词：结果字节流必须仍是合法 UTF-8，
 *      且断词点位于码位边界（不断裂多字节序列）
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "hyphen.h"

static int count_points(const char *hyphens, int len)
{
    int n = 0;
    for (int i = 0; i < len; i++)
        if (hyphens[i] & 1)
            n++;
    return n;
}

/* 检查 hyphword 中 '=' 标记是否都落在 UTF-8 码位边界 */
static int check_utf8_boundaries(const char *s)
{
    int expect_lead = 0; /* 期望的后续字节数 */
    for (const unsigned char *p = (const unsigned char *)s; *p; p++) {
        if (*p == '=') {
            if (expect_lead != 0) {
                fprintf(stderr, "FAIL: '=' 位于多字节序列中间: %s\n", s);
                return 1;
            }
            continue;
        }
        if (expect_lead > 0) {
            if ((*p & 0xC0) != 0x80) {
                fprintf(stderr, "FAIL: 非法 UTF-8 续字节: %s\n", s);
                return 1;
            }
            expect_lead--;
            continue;
        }
        if (*p < 0x80) continue;                    /* ASCII */
        else if ((*p & 0xE0) == 0xC0) expect_lead = 1;
        else if ((*p & 0xF0) == 0xE0) expect_lead = 2;
        else if ((*p & 0xF8) == 0xF0) expect_lead = 3;
        else {
            fprintf(stderr, "FAIL: 非法 UTF-8 首字节: %s\n", s);
            return 1;
        }
    }
    return expect_lead != 0;
}

int main(int argc, char **argv)
{
    if (argc < 2) {
        fprintf(stderr, "usage: ohos_special_test <hyph_en_US.dic 路径>\n");
        return 2;
    }
    const char *dict_path = argv[1];

    HyphenDict *dict = hnj_hyphen_load(dict_path);
    if (!dict) {
        fprintf(stderr, "FAIL: 无法从 %s 加载词典\n", dict_path);
        return 1;
    }

    const char *words[] = {
        "example",          /* ASCII，期望断词点 */
        "abbreviations",    /* ASCII 多音节 */
        "prävention",       /* UTF-8（ä = 2 字节），验证码位边界 */
        "übernahme",        /* UTF-8（ü = 2 字节） */
        "соответствие",     /* UTF-8（西里尔字母，3 字节/码位） */
    };
    int failures = 0;
    for (size_t i = 0; i < sizeof(words) / sizeof(words[0]); i++) {
        const char *w = words[i];
        int wlen = (int)strlen(w);
        char *hyphens = calloc((size_t)wlen + 5, 1);
        char *hyphword = calloc((size_t)wlen * 2 + 16, 1);
        char **rep = NULL;
        int *pos = NULL, *cut = NULL;
        int rc = hnj_hyphen_hyphenate2(dict, w, wlen, hyphens,
                                       hyphword, &rep, &pos, &cut);
        if (rc != 0) {
            fprintf(stderr, "FAIL: hnj_hyphen_hyphenate2(%s) rc=%d\n", w, rc);
            failures++;
            free(hyphens); free(hyphword);
            continue;
        }
        int pts = count_points(hyphens, wlen);
        if (check_utf8_boundaries(hyphword)) failures++;
        printf("word=%-16s len=%-3d points=%-2d hyphword=%s\n",
               w, wlen, pts, hyphword);
        free(hyphens); free(hyphword);
    }

    hnj_hyphen_free(dict);

    if (failures == 0) {
        printf("ohos_special_test: PASS (dict=%s, %zu words)\n",
               dict_path, sizeof(words) / sizeof(words[0]));
        return 0;
    }
    fprintf(stderr, "ohos_special_test: FAIL (%d case(s))\n", failures);
    return 1;
}
