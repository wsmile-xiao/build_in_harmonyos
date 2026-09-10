/* 消费者验证：真实调用 cmigemo 库 API 并断言行为。
 * 1) migemo_open 打开最小字典；
 * 2) migemo_query("tokyo") 生成查询正则；
 * 3) 断言返回非 NULL 且包含字典候选词；
 * 4) migemo_close 释放。 */
#include <migemo.h>
#include <stdio.h>
#include <string.h>

int main(int argc, char **argv)
{
    migemo *m;
    unsigned char *rx;

    if (argc < 2)
    {
        fprintf(stderr, "usage: consumer <migemo-dict>\n");
        return 2;
    }

    m = migemo_open(argv[1]);
    if (m == NULL || migemo_is_enable(m) == 0)
    {
        fprintf(stderr, "migemo_open failed\n");
        return 1;
    }

    rx = migemo_query(m, (unsigned char *)"tokyo");
    if (rx == NULL)
    {
        fprintf(stderr, "migemo_query returned NULL\n");
        return 1;
    }
    printf("query regex: %s\n", rx);
    if (strstr((char *)rx, "とうきょう") == NULL)
    {
        fprintf(stderr, "regex does not contain dictionary candidate\n");
        return 1;
    }
    migemo_release(m, rx);
    migemo_close(m);
    printf("cmigemo consumer test passed\n");
    return 0;
}
