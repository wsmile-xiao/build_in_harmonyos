/*
 * test_package consumer test for bptree 0.5.0 (habedi/bptree)
 *
 * R34/PF3: 必须真实调用被测包 API 并验证可观察结果，禁止空壳打印。
 * bptree 是单头文件库：在且仅在一个 TU 定义 BPTREE_IMPLEMENTATION。
 * 仅使用公开头文件 bptree.h 中的公开 API
 * (bptree_create/bptree_put/bptree_get/bptree_remove/bptree_contains/
 *  bptree_count/bptree_check_invariants/bptree_free)。
 */
#define BPTREE_IMPLEMENTATION
#include "bptree.h"

#include <stdio.h>
#include <stdlib.h>

int main(void) {
    /* 创建 max_keys=5 的数值键 B+ 树（NULL 比较器 = 默认数值比较） */
    bptree *tree = bptree_create(5, NULL, false);
    if (tree == NULL) {
        fprintf(stderr, "bptree_create failed\n");
        return 1;
    }

    /* bptree_put 插入 5 个键值对并验证 count */
    const int64_t keys[] = {42, 17, 99, 3, 77};
    for (size_t i = 0; i < sizeof(keys) / sizeof(keys[0]); i++) {
        if (bptree_put(tree, (bptree_key_t[]){keys[i]}, (bptree_value_t)(size_t)(keys[i] * 10)) != BPTREE_OK) {
            fprintf(stderr, "bptree_put(%lld) failed\n", (long long)keys[i]);
            bptree_free(tree);
            return 2;
        }
    }
    if (bptree_count(tree) != 5) {
        fprintf(stderr, "bptree_count = %d, expected 5\n", bptree_count(tree));
        bptree_free(tree);
        return 3;
    }

    /* bptree_get 检索已插入键的值 */
    bptree_value_t out = NULL;
    if (bptree_get(tree, (bptree_key_t[]){42}, &out) != BPTREE_OK || out != (bptree_value_t)(size_t)420) {
        fprintf(stderr, "bptree_get(42) failed or wrong value %p\n", out);
        bptree_free(tree);
        return 4;
    }

    /* bptree_contains 存在/不存在判断 */
    if (!bptree_contains(tree, (bptree_key_t[]){42})) {
        fprintf(stderr, "bptree_contains(42) = false, expected true\n");
        bptree_free(tree);
        return 5;
    }
    if (bptree_contains(tree, (bptree_key_t[]){1000})) {
        fprintf(stderr, "bptree_contains(1000) = true, expected false\n");
        bptree_free(tree);
        return 6;
    }

    /* bptree_remove 删除一个键并复验 */
    if (bptree_remove(tree, (bptree_key_t[]){17}) != BPTREE_OK) {
        fprintf(stderr, "bptree_remove(17) failed\n");
        bptree_free(tree);
        return 7;
    }
    if (bptree_count(tree) != 4) {
        fprintf(stderr, "bptree_count after remove = %d, expected 4\n", bptree_count(tree));
        bptree_free(tree);
        return 8;
    }
    if (bptree_contains(tree, (bptree_key_t[]){17})) {
        fprintf(stderr, "removed key 17 still contained\n");
        bptree_free(tree);
        return 9;
    }

    /* 结构不变量检查（B+ 树正确性核心） */
    if (!bptree_check_invariants(tree)) {
        fprintf(stderr, "bptree_check_invariants failed\n");
        bptree_free(tree);
        return 10;
    }

    bptree_free(tree);
    printf("bptree consumer test PASSED: create/put/get/contains/remove/invariants ok\n");
    return 0;
}