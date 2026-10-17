/*
 * ssdeep 2.8 消费者测试（test_package）
 * 仅通过已安装/导出的公开头文件 fuzzy.h 与公开 API 使用该库：
 *   fuzzy_hash_buf / fuzzy_compare
 * 验证第三方使用者能否编译、链接、调用并得到可观察结果。
 */
#include <stdio.h>
#include <string.h>

#include "fuzzy.h"

#define MAX_RESULT (FUZZY_MAX_RESULT + 16)

int main(void)
{
    char h1[MAX_RESULT], h2[MAX_RESULT];
    const char *msg = "ssdeep 2.8 test_package consumer check";
    int rc, score;

    rc = fuzzy_hash_buf((const unsigned char *)msg, strlen(msg), h1);
    if (rc != 0 || strlen(h1) == 0) {
        fprintf(stderr, "FAIL: fuzzy_hash_buf rc=%d\n", rc);
        return 1;
    }
    rc = fuzzy_hash_buf((const unsigned char *)msg, strlen(msg), h2);
    if (rc != 0 || strcmp(h1, h2) != 0) {
        fprintf(stderr, "FAIL: determinism violated\n");
        return 1;
    }
    score = fuzzy_compare(h1, h2);
    printf("consumer ok: hash=%s score(identical)=%d\n", h1, score);
    return (score >= 0) ? 0 : 1;
}
