/* consumer_fleur.c — 独立消费者验证用例（模拟业务上层组件/应用）。
 *
 * 仅通过 fleur 已安装/导出的公开头文件 <fleur.h>、公开 API
 * （fleur_initialize / fleur_add / fleur_check / fleur_bloom_filter_to_file /
 *  fleur_bloom_filter_from_file / fleur_destroy_filter）、正常链接目标
 * （-lfleur -lfnv -lmyutils）与运行时产物使用该三方库：不包含库私有头、
 * 不调用内部符号、不复用库内部测试构建目录。
 *
 * 业务场景：爬虫去重服务用 Bloom Filter 维护"已抓取 URL 集合"，
 * 批量加入一批种子 URL，随后对候选 URL 判重；将集合序列化到磁盘文件
 * （增量快照），重启后从快照恢复并继续判重 —— 覆盖 add/check/
 * 序列化往返/持久化恢复整条链路，输出可观察结果并断言。
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "fleur.h"

#define SEEDS 6
#define CANDIDATES 4

int main(void)
{
    int failures = 0;

    const char *seeds[SEEDS] = {
        "https://example.com/page/1",
        "https://example.com/page/2",
        "https://example.com/docs/api",
        "https://example.com/blog/hello",
        "https://example.com/assets/app.js",
        "https://example.com/robots.txt",
    };
    const char *candidates[CANDIDATES] = {
        "https://example.com/page/1",          /* 已抓取 → 应判重 */
        "https://example.com/page/2",          /* 已抓取 → 应判重 */
        "https://example.com/page/999",        /* 新 URL  → 应放行 */
        "https://other-site.com/entry",        /* 新 URL  → 应放行 */
    };

    /* 1. 初始化 Bloom Filter：容量 10000、误报率 0.001 */
    BloomFilter seen = fleur_initialize(10000, 0.001, "crawler-seen");
    if (seen.h.version != 1 || seen.h.k == 0) {
        fprintf(stderr, "consumer FAIL: initialize\n");
        return 1;
    }

    /* 2. 批量加入已抓取 URL */
    for (int i = 0; i < SEEDS; i++) {
        if (fleur_add(&seen, (char *)seeds[i], strlen(seeds[i])) != 1) {
            fprintf(stderr, "consumer FAIL: add(%s)\n", seeds[i]);
            failures++;
        }
    }

    /* 3. 判重：候选 URL 中种子应命中，新 URL 不应命中 */
    const int expect_hit[CANDIDATES] = {1, 1, 0, 0};
    for (int i = 0; i < CANDIDATES; i++) {
        int hit = fleur_check(&seen, (char *)candidates[i], strlen(candidates[i]));
        if (hit != expect_hit[i]) {
            fprintf(stderr, "consumer FAIL: check(%s) hit=%d expect=%d\n",
                    candidates[i], hit, expect_hit[i]);
            failures++;
        }
        printf("dedup %-38s -> %s\n", candidates[i],
               hit ? "already_crawled (skip)" : "new (crawl)");
    }

    /* 4. 序列化快照到磁盘（增量持久化） */
    const char *snap = "./consumer-fleur-seen.bloom";
    FILE *f = fopen(snap, "wb");
    if (!f || fleur_bloom_filter_to_file(&seen, f) != 1) {
        fprintf(stderr, "consumer FAIL: serialize\n");
        failures++;
    }
    if (f) fclose(f);
    fleur_destroy_filter(&seen);

    /* 5. 重启恢复：从快照重建后继续判重 */
    f = fopen(snap, "rb");
    if (!f) {
        fprintf(stderr, "consumer FAIL: reopen snapshot\n");
        failures++;
    } else {
        BloomFilter restored = fleur_bloom_filter_from_file(f);
        fclose(f);
        if (restored.error != 0) {
            fprintf(stderr, "consumer FAIL: restore\n");
            failures++;
        } else {
            for (int i = 0; i < CANDIDATES; i++) {
                int hit = fleur_check(&restored, (char *)candidates[i],
                                      strlen(candidates[i]));
                if (hit != expect_hit[i]) {
                    fprintf(stderr, "consumer FAIL: post-restore check(%s)\n",
                            candidates[i]);
                    failures++;
                }
            }
            printf("snapshot restore: %llu-bit filter rebuilt OK (k=%llu)\n",
                   (unsigned long long)restored.h.m,
                   (unsigned long long)restored.h.k);
            fleur_destroy_filter(&restored);
        }
    }
    remove(snap);

    if (failures == 0) {
        printf("consumer_fleur: PASS (seeds=%d candidates=%d)\n", SEEDS, CANDIDATES);
        return 0;
    }
    fprintf(stderr, "consumer_fleur: FAIL (%d)\n", failures);
    return 1;
}
