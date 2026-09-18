#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "maa.h"

/* 消费者测试：仅通过公开头文件 maa.h 与公开 API 使用 libmaa。
 * 验证哈希表 (hsh_*) 与字符串池 (str_pool_*) 的实际可观察行为。 */
int main(void) {
    int rc = 0;
    maa_init("libmaa-consumer-test");

    /* maa_version: 公开 API，返回版本字符串（格式 "Libmaa MAJOR.MINOR.TEENY"） */
    const char *ver = maa_version();
    printf("libmaa version: %s\n", ver);
    if (ver == NULL || strncmp(ver, "Libmaa ", 7) != 0) {
        fprintf(stderr, "FAIL: unexpected version string\n");
        rc = 1;
    }
    if (maa_version_major() != 4 || maa_version_minor() != 0 || maa_version_teeny() != 0) {
        fprintf(stderr, "FAIL: unexpected version numbers\n");
        rc = 1;
    }

    /* hsh_*: 创建哈希表，插入/检索/删除一个键值 */
    hsh_HashTable tbl = hsh_create(hsh_string_hash, hsh_string_compare);
    if (tbl == NULL) {
        fprintf(stderr, "FAIL: hsh_create returned NULL\n");
        maa_shutdown();
        return 1;
    }
    const char *k1 = "alpha";
    int v1 = 42;
    if (hsh_insert(tbl, k1, &v1) != 0) {
        fprintf(stderr, "FAIL: hsh_insert failed\n");
        rc = 1;
    }
    const void *got = hsh_retrieve(tbl, k1);
    if (got == NULL || *(const int *)got != 42) {
        fprintf(stderr, "FAIL: hsh_retrieve did not return inserted value\n");
        rc = 1;
    } else {
        printf("hsh_retrieve(alpha) = %d\n", *(const int *)got);
    }
    if (hsh_retrieve(tbl, "missing") != NULL) {
        fprintf(stderr, "FAIL: hsh_retrieve of missing key should return NULL\n");
        rc = 1;
    }
    hsh_delete(tbl, k1);
    if (hsh_retrieve(tbl, k1) != NULL) {
        fprintf(stderr, "FAIL: hsh_retrieve after delete should return NULL\n");
        rc = 1;
    }
    hsh_destroy(tbl);

    /* str_pool_*: 字符串池（str_pool_find 去重；str_pool_copy 仅复制） */
    str_Pool pool = str_pool_create();
    if (pool == NULL) {
        fprintf(stderr, "FAIL: str_pool_create returned NULL\n");
        maa_shutdown();
        return 1;
    }
    const char *s1 = str_pool_find(pool, "hello libmaa");
    const char *s2 = str_pool_find(pool, "hello libmaa");
    if (s1 == NULL || s2 == NULL) {
        fprintf(stderr, "FAIL: str_pool_find returned NULL\n");
        rc = 1;
    } else if (s1 != s2) {
        fprintf(stderr, "FAIL: str_pool_find did not intern identical strings\n");
        rc = 1;
    } else {
        printf("str_pool intern: '%s' (same ptr %d)\n", s1, s1 == s2);
    }
    if (!str_pool_exists(pool, "hello libmaa") || str_pool_exists(pool, "nope")) {
        fprintf(stderr, "FAIL: str_pool_exists wrong result\n");
        rc = 1;
    }
    str_pool_destroy(pool);

    maa_shutdown();
    if (rc == 0) {
        printf("libmaa consumer test: PASS\n");
    }
    return rc;
}
