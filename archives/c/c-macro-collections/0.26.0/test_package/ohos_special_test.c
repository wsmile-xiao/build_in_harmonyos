// ohos_special_test.c — c-macro-collections 0.26.0 鸿蒙专项测试用例
// 独立于上游测试（tests/main.c 484 用例）与 test_package/test.c（消费者冒烟）的
// HarmonyOS 专项用例：在 OHOS aarch64 工具链下真实编译运行，覆盖多个集合类型
// （hashmap/stack/heap/treemap）的构造、写入、读取与有序语义，验证公开宏 API
// 在 OHOS 平台上的完整可用性。非空壳：每个集合均有可观察结果断言。
//
// 宏实例化方式与上游 tests/unt_*.h 一致：每个 #include 前定义 V/PFX/SNAME
// （需要 K 时一并定义），头文件末尾的 cor/undef.h 自动清理这些宏。
#include <stdio.h>
#include <stdlib.h>

/* ---- hashmap: size_t -> size_t ---- */
#define V size_t
#define K size_t
#define PFX sizemap
#define SNAME size_map
#include "cmc/hashmap.h"
#include "cmc/utl/futils.h"

/* ---- stack: int ---- */
#define V int
#define PFX istack
#define SNAME int_stack
#include "cmc/stack.h"

/* ---- heap: int (max-heap) ---- */
#define V int
#define PFX iheap
#define SNAME int_heap
#include "cmc/heap.h"

/* ---- treemap: int -> int ---- */
#define V int
#define K int
#define PFX itree
#define SNAME int_treemap
#define CMC_EXT_ITER
#include "cmc/treemap.h"

int main(void)
{
    int failures = 0;

    /* 1. hashmap：插入 1000 项并回读 */
    struct size_map *map = sizemap_new(64, 0.8,
                                       &(struct size_map_fkey){ .cmp = cmc_size_cmp, .hash = cmc_size_hash, .str = cmc_size_str, .cpy = NULL, .free = NULL, .pri = cmc_size_cmp },
                                       &(struct size_map_fval){ .cmp = cmc_size_cmp, .hash = cmc_size_hash, .str = cmc_size_str, .cpy = NULL, .free = NULL, .pri = cmc_size_cmp });
    if (!map) { fprintf(stderr, "OHOS-SPECIAL: sizemap_new failed\n"); return 1; }
    for (size_t i = 0; i < 1000; i++)
        sizemap_insert(map, i, i * 2);
    if (sizemap_count(map) != 1000) { fprintf(stderr, "OHOS-SPECIAL: map count=%zu != 1000\n", sizemap_count(map)); failures++; }
    int missing = 0;
    for (size_t i = 0; i < 1000; i++)
        if (sizemap_get(map, i) != i * 2) { missing++; }
    if (missing) { fprintf(stderr, "OHOS-SPECIAL: %d map lookups wrong\n", missing); failures++; }
    sizemap_free(map);

    /* 2. stack：LIFO 语义 */
    struct int_stack *st = istack_new(16, &(struct int_stack_fval){ .cmp = cmc_i32_cmp, .hash = cmc_i32_hash, .str = cmc_i32_str, .cpy = NULL, .free = NULL, .pri = cmc_i32_cmp });
    if (!st) { fprintf(stderr, "OHOS-SPECIAL: istack_new failed\n"); return 1; }
    for (int i = 0; i < 100; i++) istack_push(st, i);
    int ok_lifo = 1;
    for (int i = 99; i >= 0; i--)
    {
        if (istack_top(st) != i) { ok_lifo = 0; break; }
        istack_pop(st);
    }
    if (!ok_lifo) { fprintf(stderr, "OHOS-SPECIAL: stack LIFO broken\n"); failures++; }
    istack_free(st);

    /* 3. heap：max-heap 出堆有序（peek 取最大，remove 移除） */
    struct int_heap *hp = iheap_new(32, CMC_MAX_HEAP, &(struct int_heap_fval){ .cmp = cmc_i32_cmp, .hash = cmc_i32_hash, .str = cmc_i32_str, .cpy = NULL, .free = NULL, .pri = cmc_i32_cmp });
    if (!hp) { fprintf(stderr, "OHOS-SPECIAL: iheap_new failed\n"); return 1; }
    for (int i = 0; i < 100; i++) iheap_insert(hp, (i * 37) % 100);
    int prev = 101, ok_desc = 1, cnt = 0;
    while (iheap_count(hp) > 0)
    {
        int m = iheap_peek(hp);
        if (m > prev) { ok_desc = 0; break; }
        prev = m;
        iheap_remove(hp);
        cnt++;
    }
    if (!ok_desc || cnt != 100) { fprintf(stderr, "OHOS-SPECIAL: heap order broken cnt=%d\n", cnt); failures++; }
    iheap_free(hp);

    /* 4. treemap：有序遍历 0..999 */
    struct int_treemap *tm = itree_new(&(struct int_treemap_fkey){ .cmp = cmc_i32_cmp, .hash = cmc_i32_hash, .str = cmc_i32_str, .cpy = NULL, .free = NULL, .pri = cmc_i32_cmp },
                                       &(struct int_treemap_fval){ .cmp = cmc_i32_cmp, .hash = cmc_i32_hash, .str = cmc_i32_str, .cpy = NULL, .free = NULL, .pri = cmc_i32_cmp });
    if (!tm) { fprintf(stderr, "OHOS-SPECIAL: itree_new failed\n"); return 1; }
    for (int i = 0; i < 1000; i++) itree_insert(tm, i, i);
    int sorted_ok = 1, last = -1;
    size_t n = 0;
    struct int_treemap_iter it = itree_iter_start(tm);
    while (!itree_iter_at_end(&it))
    {
        if (itree_iter_key(&it) <= last) { sorted_ok = 0; break; }
        last = itree_iter_key(&it);
        n++;
        itree_iter_next(&it);
    }
    if (!sorted_ok || n != 1000) { fprintf(stderr, "OHOS-SPECIAL: treemap order broken n=%zu\n", n); failures++; }
    itree_free(tm);

    if (failures)
    {
        fprintf(stderr, "OHOS-SPECIAL: %d failure(s)\n", failures);
        return 1;
    }
    printf("OHOS-SPECIAL: c-macro-collections 0.26.0 ok (hashmap1000/stackLIFO/heapMaxOrder/treemapSorted)\n");
    return 0;
}
