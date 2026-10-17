/*
 * test_package 消费者用例 — arena-allocator 20260923
 *
 * 模拟业务上层组件，仅通过公开头文件 <arena.h> 与公开 API
 * (arena_create/arena_alloc/arena_alloc_aligned/arena_clear/arena_destroy)
 * 使用该三方库：编译、链接、调用并验证可观察结果（R34 / 消费者硬门禁）。
 *
 * 实现方式：在单个 TU 中定义 ARENA_IMPLEMENTATION 由头文件展开实现
 * （上游官方用法，见 README 与 code_examples/example.c）。
 */
#include <stdio.h>
#include <string.h>

#define ARENA_IMPLEMENTATION
#include "arena.h"

int main(void) {
    /* 1. arena_create + arena_alloc：堆上 arena，分配并写入/读出数据 */
    Arena *arena = arena_create(256);
    if (!arena) {
        fprintf(stderr, "FAIL: arena_create returned NULL\n");
        return 1;
    }
    if (arena->size != 256) {
        fprintf(stderr, "FAIL: arena->size=%ld, expected 256\n", (long)arena->size);
        return 1;
    }
    char *buf = (char *)arena_alloc(arena, 6);
    if (!buf) {
        fprintf(stderr, "FAIL: arena_alloc returned NULL\n");
        return 1;
    }
    memcpy(buf, "hello", 6);
    if (memcmp(buf, "hello", 6) != 0 || arena->index != 6) {
        fprintf(stderr, "FAIL: arena_alloc round-trip broken (index=%ld)\n", (long)arena->index);
        return 1;
    }
    printf("arena_alloc round-trip: ok (index=%ld, data='%s')\n", (long)arena->index, buf);

    /* 2. arena_alloc_aligned：对齐分配 */
    void *p = arena_alloc_aligned(arena, 14, 16);
    if (!p || ((unsigned long)p % 16) != 0) {
        fprintf(stderr, "FAIL: arena_alloc_aligned alignment=16 broken (p=%p)\n", p);
        return 1;
    }
    printf("arena_alloc_aligned: ok (p=%p, index=%ld)\n", p, (long)arena->index);

    /* 3. arena_clear + 复用 */
    arena_clear(arena);
    if (arena->index != 0) {
        fprintf(stderr, "FAIL: arena_clear did not reset index (index=%ld)\n", (long)arena->index);
        return 1;
    }
    char *again = (char *)arena_alloc(arena, 4);
    if (!again) {
        fprintf(stderr, "FAIL: realloc after arena_clear returned NULL\n");
        return 1;
    }
    printf("arena_clear + reuse: ok\n");

    /* 4. arena_destroy 释放 */
    arena_destroy(arena);
    printf("arena-destroy: ok\n");

    printf("test arena-allocator 20260923: OK\n");
    return 0;
}
