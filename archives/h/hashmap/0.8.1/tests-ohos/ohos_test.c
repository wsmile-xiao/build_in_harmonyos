/* OHOS 专项测试：通过公开 API 验证 hashmap 在 HarmonyOS PC (armv8, OHOS clang)
 * 平台上的完整功能与可观察结果（与上游 HASHMAP_TEST 自检、test_package 消费者
 * 用例分别计数）。
 *
 * 验证点：
 *   1. hash 函数向量（hashmap_sip/murmur/xxhash3 已知值，与上游断言一致）
 *   2. 插入/更新/查找/删除/计数/迭代/清空（含自定义分配器挂钩）
 *   3. hashmap_scan 全量遍历
 *   4. 内存回收完整性（自定义分配器跟踪 alloc_count 归零）
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include "hashmap.h"

/* ---- 自定义分配器（验证 allocator 挂钩与内存回收） ---- */
static uintptr_t alloc_count = 0;

static void *ohos_malloc(size_t size) {
    alloc_count++;
    return malloc(size);
}
static void *ohos_realloc(void *ptr, size_t size) {
    return realloc(ptr, size);
}
static void ohos_free(void *ptr) {
    if (ptr) {
        alloc_count--;
    }
    free(ptr);
}

/* ---- 键类型 ---- */
typedef struct {
    char key[24];
    int value;
} Entry;

static uint64_t entry_hash(const void *item, uint64_t seed0, uint64_t seed1) {
    const Entry *e = item;
    return hashmap_xxhash3(e->key, strlen(e->key), seed0, seed1);
}

static int entry_compare(const void *a, const void *b, void *udata) {
    (void)udata;
    return strcmp(((const Entry *)a)->key, ((const Entry *)b)->key);
}

static bool scan_sum(const void *item, void *udata) {
    int *sum = udata;
    *sum += ((const Entry *)item)->value;
    return true;
}

#define CHECK(cond, msg) do { \
    if (!(cond)) { \
        fprintf(stderr, "OHOS test FAILED: %s (line %d)\n", msg, __LINE__); \
        return 1; \
    } \
} while (0)

int main(void) {
    /* 1. 哈希向量（与上游 all() 断言相同的已知值，验证 OHOS 平台一致性） */
    CHECK(hashmap_sip("hello", 5, 1, 2) == 2957200328589801622ULL, "sip vector");
    CHECK(hashmap_murmur("hello", 5, 1, 2) == 1682575153221130884ULL, "murmur vector");
    CHECK(hashmap_xxhash3("hello", 5, 1, 2) == 2584346877953614258ULL, "xxhash3 vector");

    /* 2. 基础 CRUD（默认分配器） */
    struct hashmap *map = hashmap_new(sizeof(Entry), 0, 42, 42,
                                      entry_hash, entry_compare, NULL, NULL);
    CHECK(map != NULL, "hashmap_new");

    Entry a = {"alpha", 1}, b = {"beta", 2}, c = {"gamma", 3};
    hashmap_set(map, &a);
    CHECK(!hashmap_oom(map), "set alpha");
    hashmap_set(map, &b);
    CHECK(!hashmap_oom(map), "set beta");
    hashmap_set(map, &c);
    CHECK(!hashmap_oom(map), "set gamma");
    CHECK(hashmap_count(map) == 3, "count==3");

    const Entry *got = hashmap_get(map, &b);
    CHECK(got != NULL && got->value == 2, "get beta");

    b.value = 22; /* 更新：替换已有项，返回旧项指针 */
    const void *old = hashmap_set(map, &b);
    CHECK(old != NULL, "update returns old item");
    got = hashmap_get(map, &b);
    CHECK(got != NULL && got->value == 22, "get updated beta");

    /* 3. hashmap_scan 全量遍历求和 */
    int sum = 0;
    CHECK(hashmap_scan(map, scan_sum, &sum), "scan");
    CHECK(sum == 1 + 22 + 3, "scan sum == 26");

    /* iter 统计总数 */
    size_t iter = 0;
    void *item;
    size_t n = 0;
    while (hashmap_iter(map, &iter, &item)) {
        n++;
    }
    CHECK(n == 3, "iter count==3");

    /* 4. 删除与清空 */
    CHECK(hashmap_delete(map, &a) != NULL, "delete alpha");
    CHECK(hashmap_count(map) == 2, "count==2 after delete");
    hashmap_clear(map, false);
    CHECK(hashmap_count(map) == 0, "count==0 after clear");
    hashmap_free(map);

    /* 5. 自定义分配器挂钩 + 内存回收归零 */
    alloc_count = 0;
    struct hashmap *m2 = hashmap_new_with_allocator(
        ohos_malloc, ohos_realloc, ohos_free,
        sizeof(Entry), 0, 7, 7, entry_hash, entry_compare, NULL, NULL);
    CHECK(m2 != NULL, "hashmap_new_with_allocator");
    CHECK(alloc_count > 0, "allocator engaged");

    for (int i = 0; i < 100; i++) {
        Entry e;
        snprintf(e.key, sizeof(e.key), "k%03d", i);
        e.value = i;
        hashmap_set(m2, &e);
        CHECK(!hashmap_oom(m2), "bulk set");
    }
    CHECK(hashmap_count(m2) == 100, "bulk count==100");

    /* 扩容压力（5000 项触发 grow 路径） */
    for (int i = 0; i < 5000; i++) {
        Entry e;
        snprintf(e.key, sizeof(e.key), "g%05d", i);
        e.value = i;
        hashmap_set(m2, &e);
        CHECK(!hashmap_oom(m2), "grow set");
    }
    CHECK(hashmap_count(m2) == 5100, "grow count==5100");

    Entry probe = {"g04999", 0};
    got = hashmap_get(m2, &probe);
    CHECK(got != NULL && got->value == 4999, "grow get");

    hashmap_free(m2);
    CHECK(alloc_count == 0, "allocator fully released");

    printf("OHOS test PASSED\n");
    return 0;
}
