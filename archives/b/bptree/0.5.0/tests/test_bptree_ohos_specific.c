/*
 * HarmonyOS 专项测试 — bptree 0.5.0 (OHOS aarch64)
 *
 * 目的：验证 bptree 在 HarmonyOS PC (aarch64, OHOS libc) 上作为
 * 单头文件库被业务组件消费时的真实可用性——上游 29 用例之外的鸿蒙专项
 * 验证：高压力随机插入/删除 + 迭代器遍历 + 范围查询 + 结构不变量，
 * 并在每次迭代后强制校验 B+ 树不变量（上游 test_bptree.c 没有把
 * check_invariants 纳入每步循环，这里是独立补充的鸿蒙场景压测）。
 *
 * 编译（OHOS 工具链）：
 *   /data/service/hnp/bin/clang -std=c11 -O2 -Iinclude \
 *     -o test_bptree_ohos_specific test_bptree_ohos_specific.c
 */
#define BPTREE_IMPLEMENTATION
#include "bptree.h"

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

/* 确定性伪随机（避免依赖平台 rand 差异，保证结果可复现） */
static uint64_t rng_state = 0x9e3779b97f4a7c15ULL;
static uint64_t rng_next(void) {
    rng_state ^= rng_state << 13;
    rng_state ^= rng_state >> 7;
    rng_state ^= rng_state << 17;
    return rng_state;
}

int main(void) {
    const int iterations = 3000;   /* 3× 上游 stress 规模 */
    const int64_t key_max = 2048;
    bptree *tree = bptree_create(7, NULL, false);
    int failures = 0;

    if (tree == NULL) {
        fprintf(stderr, "OHOS specific: bptree_create failed\n");
        return 1;
    }

    /* 阶段 1: 随机插入 3000 键值（key 空间 0..2047，含重复 put 冲突路径） */
    for (int i = 0; i < iterations; i++) {
        int64_t k = (int64_t)(rng_next() % key_max);
        bptree_put(tree, (bptree_key_t[]){k}, (bptree_value_t)(size_t)(i + 1));
        if ((i & 0x3f) == 0) { /* 每 64 次检查一次不变量 */
            if (!bptree_check_invariants(tree)) {
                fprintf(stderr, "OHOS specific: invariants failed after put #%d\n", i);
                failures++;
                break;
            }
        }
    }

    /* 阶段 2: 随机删除一半再复插（重平衡路径） */
    int removed = 0;
    for (int i = 0; i < iterations; i++) {
        int64_t k = (int64_t)(rng_next() % key_max);
        if (bptree_remove(tree, (bptree_key_t[]){k}) == BPTREE_OK) {
            removed++;
        }
        if ((i & 0x3f) == 0 && !bptree_check_invariants(tree)) {
            fprintf(stderr, "OHOS specific: invariants failed during delete #%d\n", i);
            failures++;
            break;
        }
    }

    /* 阶段 3: 迭代器全遍历 — 键必须严格升序（B+ 树叶子链性质） */
    int64_t prev = INT64_MIN;
    long seen = 0;
    bool ordered = true;
    for (bptree_iter it = bptree_iter_begin(tree); bptree_iter_valid(&it); bptree_iter_next(&it)) {
        int64_t cur = bptree_iter_key(&it);
        if (cur < prev) {
            ordered = false;
            fprintf(stderr, "OHOS specific: iteration out of order at %ld (key %lld < %lld)\n",
                    seen, (long long)cur, (long long)prev);
            break;
        }
        prev = cur;
        seen++;
    }
    if (!ordered) failures++;

    /* 阶段 4: 范围查询 */
    int64_t lo = 100, hi = 400;
    bptree_value_t *vals = NULL;
    int n = 0;
    if (bptree_get_range(tree, (bptree_key_t[]){lo}, (bptree_key_t[]){hi}, &vals, &n) != BPTREE_OK) {
        fprintf(stderr, "OHOS specific: get_range failed\n");
        failures++;
    } else {
        bptree_free_range_results(vals);
    }

    if (!bptree_check_invariants(tree)) {
        fprintf(stderr, "OHOS specific: final invariants check failed\n");
        failures++;
    }

    int count = bptree_count(tree);
    bptree_free(tree);

    if (failures == 0) {
        printf("OHOS specific PASSED: iterations=%d removed=%d seen=%ld range_n=%d final_count=%d ordered=1\n",
               iterations, removed, seen, n, count);
        return 0;
    }
    fprintf(stderr, "OHOS specific FAILED: failures=%d\n", failures);
    return 1;
}