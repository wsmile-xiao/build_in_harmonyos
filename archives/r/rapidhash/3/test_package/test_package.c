/* test_package.c — rapidhash/3 消费方测试（C99 消费路径）。
 *
 * 789 组冻结 KAT 向量（vectors.h，自未修改 rapidhash_v3 tarball 生成）
 * + 上游 README 文档化属性断言（种子敏感性；rapidhashMicro 与 rapidhash
 *   在 <=80 字节等值；rapidhashNano 与 rapidhash 在 <=48 字节等值）。
 * 全部为运行期真实比较（P2738 限制见 notes.md/E560），非 print-only。
 */
#include <rapidhash/rapidhash.h>
#include "vectors.h"

#include <stdio.h>
#include <string.h>

static void fill_buf(uint8_t *buf, size_t len) {
    for (size_t i = 0; i < len; i++) buf[i] = (uint8_t)((i * 31 + 7) & 0xFF);
}

int main(void) {
    static uint8_t buf[256];
    int fails = 0, pass = 0;
    const size_t nvec = sizeof(RAPID_VECTORS) / sizeof(RAPID_VECTORS[0]);

    /* 1) frozen known-answer vectors */
    for (size_t v = 0; v < nvec; v++) {
        const rapid_vec *e = &RAPID_VECTORS[v];
        fill_buf(buf, e->len);
        uint64_t got;
        if (strcmp(e->fn, "rapidhash") == 0)
            got = e->seed ? rapidhash_withSeed(buf, e->len, e->seed)
                          : rapidhash(buf, e->len);
        else if (strcmp(e->fn, "rapidhashMicro") == 0)
            got = e->seed ? rapidhashMicro_withSeed(buf, e->len, e->seed)
                          : rapidhashMicro(buf, e->len);
        else if (strcmp(e->fn, "rapidhashNano") == 0)
            got = e->seed ? rapidhashNano_withSeed(buf, e->len, e->seed)
                          : rapidhashNano(buf, e->len);
        else { printf("FAIL: unknown fn %s\n", e->fn); return 1; }
        if (got != e->want) {
            printf("FAIL: %s len=%zu seed=0x%016llx got=0x%016llx want=0x%016llx\n",
                   e->fn, e->len, (unsigned long long)e->seed,
                   (unsigned long long)got, (unsigned long long)e->want);
            fails++;
        } else {
            pass++;
        }
    }

    /* 2) determinism */
    fill_buf(buf, 200);
    if (rapidhash(buf, 200) != rapidhash(buf, 200)) {
        printf("FAIL: nondeterministic result\n"); fails++;
    } else {
        pass++;
    }

    /* 3) seed sensitivity: distinct seeds must not collide on fixed inputs */
    {
        static const size_t ls[] = {0, 1, 2, 3, 4, 8, 16, 48, 80, 128, 256};
        for (size_t i = 0; i < sizeof(ls) / sizeof(ls[0]); i++) {
            fill_buf(buf, ls[i]);
            const uint64_t a = rapidhash_withSeed(buf, ls[i], 0);
            const uint64_t b = rapidhash_withSeed(buf, ls[i], 0x9E3779B97F4A7C15ULL);
            const uint64_t c = rapidhash_withSeed(buf, ls[i], 0xDEADBEEFCAFEF00DULL);
            if (a == b || a == c || b == c) {
                printf("FAIL: seed collision at len=%zu\n", ls[i]); fails++;
            } else {
                pass += 3;
            }
        }
    }

    /* 4) README-documented equivalence:
     *    rapidhashMicro == rapidhash up to 80 bytes;
     *    rapidhashNano  == rapidhash up to 48 bytes */
    {
        static const size_t ms[] = {0, 1, 7, 48, 80};
        static const size_t ns[] = {0, 1, 7, 48};
        for (size_t i = 0; i < sizeof(ms) / sizeof(ms[0]); i++) {
            fill_buf(buf, ms[i]);
            if (rapidhash(buf, ms[i]) != rapidhashMicro(buf, ms[i])) {
                printf("FAIL: rapidhashMicro != rapidhash at len=%zu\n", ms[i]); fails++;
            } else {
                pass++;
            }
        }
        for (size_t i = 0; i < sizeof(ns) / sizeof(ns[0]); i++) {
            fill_buf(buf, ns[i]);
            if (rapidhash(buf, ns[i]) != rapidhashNano(buf, ns[i])) {
                printf("FAIL: rapidhashNano != rapidhash at len=%zu\n", ns[i]); fails++;
            } else {
                pass++;
            }
        }
    }

    printf("%s: %d checks passed, %d failed (frozen vectors=%zu)\n",
           fails ? "FAIL" : "OK", pass, fails, nvec);
    return fails ? 1 : 0;
}
