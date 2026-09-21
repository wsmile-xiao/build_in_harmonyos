/*
 * 消费者验证用例：模拟业务上层组件/应用，仅通过 hyphen 库第三方使用者视角
 * 使用该库 —— 只包含已安装的公开头文件 <hyphen.h>、只调用公开 API
 * （hnj_hyphen_load / hnj_hyphen_hyphenate3 / hnj_hyphen_free）、正常链接
 * -lhyphen，并使用运行时产物（libhyphen.so）。不引用库私有头文件、不调用
 * 内部符号、不复用库内部测试构建目录。
 *
 * 场景：文档排版组件需要对英文单词做断行，它从共享词典加载后对一批
 * 单词打断词点，并按其结果排版（此处打印可观察结果并断言）。
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "hyphen.h"

#define MAX_WORDS 8

struct case_t {
    const char *word;
    int lhmin;
    int rhmin;
    int expect_points;   /* 期望的断词点数（>=1 或 0） */
};

static int count_points(const char *hyph, int len)
{
    int n = 0;
    for (int i = 0; i < len; i++)
        if (hyph[i] & 1)
            n++;
    return n;
}

int main(int argc, char **argv)
{
    if (argc < 2) {
        fprintf(stderr, "usage: consumer_hyphen <hyph_en_US.dic 路径>\n");
        return 2;
    }

    HyphenDict *dict = hnj_hyphen_load(argv[1]);
    if (!dict) {
        fprintf(stderr, "consumer FAIL: hnj_hyphen_load(%s) = NULL\n", argv[1]);
        return 1;
    }

    struct case_t cases[MAX_WORDS] = {
        {"hyphenation", 2, 2, 1},
        {"computer",    2, 3, 1},
        {"cat",         2, 3, 0},
        {"abbreviation",2, 2, 1},
        {"international",2, 2, 1},
        {"organization",2, 3, 1},
        {"linux",       2, 2, 0},
        {"valediction", 2, 3, 1},
    };

    int failures = 0;
    for (int i = 0; i < MAX_WORDS; i++) {
        const char *w = cases[i].word;
        int wlen = (int)strlen(w);
        char *hyphens = calloc((size_t)wlen + 5, 1);
        char *hyphword = calloc((size_t)wlen * 2 + 16, 1);
        char **rep = NULL;
        int *pos = NULL, *cut = NULL;

        int rc = hnj_hyphen_hyphenate3(dict, w, wlen, hyphens, hyphword,
                                       &rep, &pos, &cut,
                                       cases[i].lhmin, cases[i].rhmin,
                                       cases[i].lhmin, cases[i].rhmin);
        if (rc != 0) {
            fprintf(stderr, "consumer FAIL: hyphenate3(%s) rc=%d\n", w, rc);
            failures++;
        } else {
            int pts = count_points(hyphens, wlen);
            if ((pts > 0) != (cases[i].expect_points > 0)) {
                fprintf(stderr,
                        "consumer FAIL: %s expect_points=%s got=%d (hyphword=%s)\n",
                        w, cases[i].expect_points ? "yes" : "no", pts, hyphword);
                failures++;
            }
            /* 排版行输出 = 可观察业务结果 */
            printf("layout %-2d: %s  (points=%d)\n", i, hyphword, pts);
        }
        free(hyphens);
        free(hyphword);
    }

    hnj_hyphen_free(dict);

    if (failures == 0) {
        printf("consumer_hyphen: PASS (%d layouts rendered)\n", MAX_WORDS);
        return 0;
    }
    fprintf(stderr, "consumer_hyphen: FAIL (%d)\n", failures);
    return 1;
}