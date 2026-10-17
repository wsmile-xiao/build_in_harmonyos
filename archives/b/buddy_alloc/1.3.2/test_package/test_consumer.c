/*
 * test_consumer.c — buddy_alloc 消费者用例
 *
 * 模拟业务上层组件/应用：仅通过 buddy_alloc 已安装/导出的公开头文件与
 * 公开 API 使用该三方库（buddy_init / buddy_malloc / buddy_free /
 * buddy_alloc_size / buddy_arena_free_size）。编译、链接、运行并校验
 * 可观察结果（分配地址、释放后 arena 空闲空间恢复、分配大小）。
 */
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define BUDDY_ALLOC_IMPLEMENTATION
#include "buddy_alloc.h"

int main(void)
{
    size_t arena_size = 1 << 20; /* 1 MiB */
    void *meta = malloc(buddy_sizeof(arena_size));
    unsigned char *arena = malloc(arena_size);
    struct buddy *b = buddy_init(meta, arena, arena_size);

    assert(b != NULL);
    assert(buddy_arena_size(b) == arena_size);
    size_t free_before = buddy_arena_free_size(b);

    /* 业务上层典型用法：多次分配/写/读/释放 */
    void *p1 = buddy_malloc(b, 4096);
    assert(p1 != NULL);
    memset(p1, 0xAB, 2048);
    assert(buddy_alloc_size(b, p1) >= 4096);
    assert(((unsigned char *)p1)[1024] == 0xAB);

    void *p2 = buddy_malloc(b, 65536);
    assert(p2 != NULL);
    memset(p2, 0xCD, 1024);
    assert(((unsigned char *)p2)[512] == 0xCD);

    buddy_free(b, p1);
    buddy_free(b, p2);
    size_t free_after = buddy_arena_free_size(b);

    /* 释放后空闲空间应恢复（buddy 分配器无碎片下的精确语义） */
    assert(free_after == free_before);

    printf("[consumer] arena_size=%zu free_before=%zu free_after=%zu "
           "alloc_size(p1)=%zu p2_byte=0xCD OK\n",
           arena_size, free_before, free_after, buddy_alloc_size(b, p1));
    printf("[consumer] PASS: buddy_alloc public API verified via consumer app\n");

    free(arena);
    free(meta);
    return 0;
}
