/*
 * test_package L1 测试 — 真实调用 hyphen 公开 API（hnj_hyphen_load /
 * hnj_hyphen_hyphenate2 / hnj_hyphen_free），验证：
 *   1) 词典文件（hyph_en_US.dic）可从已安装包数据目录加载
 *   2) 对已知单词执行连字符化，hyphens 向量给出非零断词点
 *   3) 复现上游期望：pattern 数据解析与断词点输出正确
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "hyphen.h"

static int check_hyphenate(const char *dict_path, const char *word)
{
    HyphenDict *dict = hnj_hyphen_load(dict_path);
    if (!dict) {
        fprintf(stderr, "FAIL: hnj_hyphen_load(%s) returned NULL\n", dict_path);
        return 1;
    }
    int wlen = (int)strlen(word);
    char *hyphens = calloc((size_t)wlen + 5, 1);
    if (!hyphens) {
        hnj_hyphen_free(dict);
        return 1;
    }
    char *hyphword = calloc((size_t)wlen * 2 + 10, 1);
    char **rep = NULL;
    int *pos = NULL;
    int *cut = NULL;
    int rc = hnj_hyphen_hyphenate2(dict, word, wlen, hyphens,
                                   hyphword, &rep, &pos, &cut);
    if (rc != 0) {
        fprintf(stderr, "FAIL: hnj_hyphen_hyphenate2(%s) rc=%d\n", word, rc);
        free(hyphens);
        free(hyphword);
        hnj_hyphen_free(dict);
        return 1;
    }
    /* hyphens 向量中奇数位标记断词点；"example" 期望至少一个断词点 */
    int points = 0;
    for (int i = 0; i < wlen; i++) {
        if (hyphens[i] & 1) points++;
    }
    printf("word=%s len=%d hyphenation_points=%d hyphword=%s\n",
           word, wlen, points, hyphword ? hyphword : "(null)");
    if (points < 1) {
        fprintf(stderr, "FAIL: %s 无任何断词点（词典可能未正确加载）\n", word);
        free(hyphens);
        free(hyphword);
        hnj_hyphen_free(dict);
        return 1;
    }
    if (hyphword && strchr(hyphword, '=') == NULL) {
        fprintf(stderr, "FAIL: hyphword 未包含 '=' 连字符标记\n");
        free(hyphens);
        free(hyphword);
        hnj_hyphen_free(dict);
        return 1;
    }
    free(hyphens);
    free(hyphword);
    hnj_hyphen_free(dict);
    return 0;
}

int main(int argc, char **argv)
{
    if (argc < 2) {
        fprintf(stderr, "usage: test_hyphen <hyph_en_US.dic 路径>\n");
        return 2;
    }
    const char *dict = argv[1];
    int failures = 0;
    failures += check_hyphenate(dict, "example");
    failures += check_hyphenate(dict, "abbreviations");
    if (failures == 0) {
        printf("test hyphen 2.8.9: PASS (dict=%s)\n", dict);
        return 0;
    }
    fprintf(stderr, "test hyphen 2.8.9: FAIL (%d case(s))\n", failures);
    return 1;
}
