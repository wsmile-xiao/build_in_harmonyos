/*
 * test_ohos.c — HarmonyOS 专项测试（区别于上游 tests.c 的独立用例）
 *
 * 针对本平台（OHOS aarch64 / clang 15）验证 buddy_alloc 的适配语义：
 *   1. 64 字节对齐 arena（对齐/最小分配单元语义）
 *   2. buddy_embed 内嵌元数据模式（不依赖外部 metadata 缓冲）
 *   3. buddy_resize 扩张/收缩与 buddy_can_shrink
 *   4. buddy_safe_free 双重释放保护（可观测结果）
 *   5. 大 arena（256 MiB）分配往返
 * 全部断言 + 可观察输出，实跑通过。
 */
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define BUDDY_ALLOC_IMPLEMENTATION
#include "buddy_alloc.h"

int main(void)
{
    /* 1. 64 字节对齐 arena */
    size_t arena_size = 1 << 18; /* 256 KiB */
    unsigned char *meta = malloc(buddy_sizeof_alignment(arena_size, 64));
    unsigned char *arena = malloc(arena_size);
    struct buddy *b = buddy_init_alignment(meta, arena, arena_size, 64);
    assert(b != NULL);
    void *p = buddy_malloc(b, 100);
    assert(p != NULL);
    assert(((uintptr_t)p & 63) == 0); /* 对齐语义：返回指针按 64 对齐 */
    buddy_free(b, p);
    printf("[ohos] alignment=64 arena=%zu aligned_ptr=%s OK\n",
           arena_size, ((uintptr_t)p & 63) == 0 ? "yes" : "no");
    free(meta);
    free(arena);

    /* 2. embed 内嵌元数据模式 */
    unsigned char *buf = malloc(1 << 16);
    struct buddy *eb = buddy_embed(buf, 1 << 16);
    assert(eb != NULL);
    void *e1 = buddy_malloc(eb, 128);
    assert(e1 != NULL);
    assert(buddy_get_embed_at(buf, 1 << 16) != NULL);
    buddy_free(eb, e1);
    free(buf);
    printf("[ohos] embed mode OK\n");

    /* 3. resize 语义 */
    {
        unsigned char *m = malloc(buddy_sizeof(1 << 20));
        unsigned char *a = malloc(1 << 20);
        struct buddy *rb = buddy_init(m, a, 1 << 20);
        void *r1 = buddy_malloc(rb, 4096);
        struct buddy *r2 = buddy_resize(rb, 2 << 20);
        assert(r2 == rb || r2 != NULL);
        buddy_free(rb, r1);
        assert(buddy_can_shrink(rb) == true);
        free(a);
        free(m);
    }
    printf("[ohos] resize semantics OK\n");

    /* 4. safe_free 双重释放保护 */
    {
        unsigned char *m = malloc(buddy_sizeof(1 << 16));
        unsigned char *a = malloc(1 << 16);
        struct buddy *sb = buddy_init(m, a, 1 << 16);
        void *s1 = buddy_malloc(sb, 64);
        enum buddy_safe_free_status s1r =
            buddy_safe_free(sb, s1, 64);   /* 第一次：正常释放 */
        assert(s1r == BUDDY_SAFE_FREE_SUCCESS);
        enum buddy_safe_free_status s2r =
            buddy_safe_free(sb, s1, 64);   /* 第二次：应被保护（非 SUCCESS） */
        assert(s2r != BUDDY_SAFE_FREE_SUCCESS);
        printf("[ohos] safe_free double-free protection OK "
               "(first=SUCCESS second=%d)\n", (int)s2r);
        free(a);
        free(m);
    }

    /* 5. 大 arena 往返 */
    {
        size_t big = 1 << 28; /* 256 MiB */
        unsigned char *m = malloc(buddy_sizeof(big));
        unsigned char *a = malloc(big);
        struct buddy *bb = buddy_init(m, a, big);
        void *bp = buddy_malloc(bb, big / 2);
        assert(bp != NULL);
        memset(bp, 0x11, 1024);
        assert(((unsigned char *)bp)[512] == 0x11);
        buddy_free(bb, bp);
        assert(buddy_is_empty(bb));
        printf("[ohos] large arena (256MiB) roundtrip OK\n");
        free(a);
        free(m);
    }

    printf("[ohos] PASS: HarmonyOS-specific buddy_alloc validation\n");
    return 0;
}
