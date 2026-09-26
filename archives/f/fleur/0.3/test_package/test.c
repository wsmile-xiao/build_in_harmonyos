#include <stdio.h>
#include <string.h>
#include "fleur.h"

/* test_package L1 测试：从消费者视角调用 fleur 公开 API，
 * 验证可链接、可运行、可观察结果（R34：禁止只打印字符串的空壳测试）。 */
int main(void)
{
    BloomFilter bf = fleur_initialize(10000, 0.001, "test-package");
    if (bf.h.version != 1) {
        fprintf(stderr, "FAIL: initialize version\n");
        return 1;
    }
    if (bf.h.n != 10000) {
        fprintf(stderr, "FAIL: initialize n\n");
        return 1;
    }

    const char *item = "conan-l1-test-item";
    if (fleur_add(&bf, (char *)item, strlen(item)) != 1) {
        fprintf(stderr, "FAIL: add\n");
        return 1;
    }
    if (fleur_check(&bf, (char *)item, strlen(item)) != 1) {
        fprintf(stderr, "FAIL: check present\n");
        return 1;
    }
    const char *absent = "not-added-value";
    if (fleur_check(&bf, (char *)absent, strlen(absent)) != 0) {
        fprintf(stderr, "FAIL: check absent\n");
        return 1;
    }

    printf("test fleur 0.3: OK (k=%llu m=%llu)\n",
           (unsigned long long)bf.h.k, (unsigned long long)bf.h.m);
    fleur_destroy_filter(&bf);
    return 0;
}