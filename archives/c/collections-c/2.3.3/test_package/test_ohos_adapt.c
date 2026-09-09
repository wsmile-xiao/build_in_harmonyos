/* test_ohos_adapt.c — collections-c 2.3.3 鸿蒙专项适配测试
 *
 * 真实执行库 API，验证 HarmonyOS(arm64) 目标上的平台关键行为：
 *   1) 内存池的 alignment_boundary 能力：以 16 字节对齐边界配置
 *      cc_dynamic_pool（libc malloc 在 aarch64-ohos 上满足 max_align_t=16），
 *      验证池内分配块全部满足 16 字节对齐（对齐选项真实生效）；
 *   2) 高频容器压力场景（hashtable + array + stack，各 2 万次操作）在 OHOS
 *      上稳定运行，检验内存分配/释放循环无崩溃、无统计错乱。
 * 该测试独立于通用 test_package 冒烟（test.c），不重复上游 munit 用例。
 */
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include "cc_array.h"
#include "cc_hashtable.h"
#include "cc_stack.h"
#include "memory/cc_dynamic_pool.h"

#define ALIGN 16
#define STRESS_N 20000

static size_t int_hash(const void *key, int l, uint32_t seed) {
    (void)l;
    uint32_t v = (uint32_t)(uintptr_t)key;
    v ^= v >> 16;
    v *= 0x85ebca6bU;
    v ^= v >> 13;
    return (size_t)(v ^ seed);
}

static int int_cmp(const void *a, const void *b) {
    return (int)((uintptr_t)a - (uintptr_t)b);
}

static int check_align(const void *p) {
    return ((uintptr_t)p % ALIGN) == 0;
}

static int pool_alignment_test(void) {
    /* 默认池是 packed（alignment_boundary=1，无对齐保证）；显式配置对齐边界
     * 来验证库的对齐能力在 OHOS 上真实生效。 */
    CC_DynamicPoolConf conf;
    cc_dynamic_pool_conf_init(&conf);
    conf.is_packed           = false;
    conf.alignment_boundary  = ALIGN;
    conf.exp_factor          = 2.0f;

    CC_DynamicPool *pool = NULL;
    if (cc_dynamic_pool_new_conf(4096, &conf, &pool) != CC_OK)
        return 1;
    int ok = 1;
    size_t sizes[] = {1, 3, 8, 16, 17, 64, 127, 256, 1000};
    for (size_t i = 0; i < sizeof(sizes) / sizeof(sizes[0]); i++) {
        void *p = cc_dynamic_pool_malloc(sizes[i], pool);
        if (!p || !check_align(p)) {
            fprintf(stderr, "pool malloc(%zu) misaligned or NULL: %p\n", sizes[i], p);
            ok = 0;
        }
    }
    cc_dynamic_pool_destroy(pool);
    return ok ? 0 : 1;
}

static int stress_test(void) {
    /* 上游默认 hashtable 按字符串 key 哈希/比较；本测试用整数指针 key，
       需显式配置整数哈希与比较，否则字节串相同的 int（如 256 的倍数）
       会被误判为重复 key。 */
    CC_HashTableConf htc;
    cc_hashtable_conf_init(&htc);
    htc.hash        = int_hash;
    htc.key_compare = int_cmp;

    CC_HashTable *ht = NULL;
    CC_Array *ar = NULL;
    CC_Stack *st = NULL;
    if (cc_hashtable_new_conf(&htc, &ht) != CC_OK) return 1;
    if (cc_array_new(&ar) != CC_OK) return 1;
    if (cc_stack_new(&st) != CC_OK) return 1;

    static int keys[STRESS_N];
    static int vals[STRESS_N];
    for (int i = 0; i < STRESS_N; i++) {
        keys[i] = i;
        vals[i] = i * 3;
        if (cc_hashtable_add(ht, &keys[i], &vals[i]) != CC_OK) { cc_hashtable_destroy(ht); return 1; }
        if (cc_array_add(ar, &vals[i]) != CC_OK) { cc_hashtable_destroy(ht); return 1; }
        if (cc_stack_push(st, &keys[i]) != CC_OK) { cc_hashtable_destroy(ht); return 1; }
    }
    if (cc_hashtable_size(ht) != STRESS_N || cc_array_size(ar) != STRESS_N || cc_stack_size(st) != STRESS_N) {
        fprintf(stderr, "size mismatch after fill\n");
        cc_hashtable_destroy(ht);
        return 1;
    }
    /* remove half of the hashtable entries, verify a couple of survivors */
    for (int i = 0; i < STRESS_N; i += 2) {
        void *out = NULL;
        cc_hashtable_remove(ht, &keys[i], &out);
    }
    if (cc_hashtable_size(ht) != STRESS_N / 2) {
        fprintf(stderr, "size mismatch after removes\n");
        cc_hashtable_destroy(ht);
        return 1;
    }
    void *got = NULL;
    if (cc_hashtable_get(ht, &keys[1], &got) != CC_OK || *(int *)got != 3) {
        fprintf(stderr, "survivor key lookup failed\n");
        cc_hashtable_destroy(ht);
        return 1;
    }
    cc_hashtable_destroy(ht);
    cc_array_destroy(ar);
    cc_stack_destroy(st);
    return 0;
}

int main(void) {
    int rc = pool_alignment_test();
    if (rc != 0) {
        fprintf(stderr, "OHOS pool alignment test FAILED (rc=%d)\n", rc);
        return rc;
    }
    printf("OHOS pool alignment (16-byte boundary) OK\n");

    rc = stress_test();
    if (rc != 0) {
        fprintf(stderr, "OHOS stress test FAILED (rc=%d)\n", rc);
        return rc;
    }
    printf("OHOS stress test (%d ops per container) OK\n", STRESS_N);
    printf("collections-c OHOS adaptation test: PASS\n");
    return 0;
}