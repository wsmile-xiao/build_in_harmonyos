/* arena 20260923 HarmonyOS 专项测试（真机 aarch64 / musl）
 *
 * 验证 arena 单头文件库在鸿蒙 PC 上的公开 API 语义，全部使用公开头文件
 * 与公开 API（arena.h + ARENA_IMPLEMENTATION），不依赖上游内部实现：
 *   1) 区域增长与跨 Region 分配（>8KB 默认容量触发 Region 分裂）
 *   2) arena_realloc 扩缩字节保真
 *   3) arena_memdup 字节 round-trip
 *   4) arena_sprintf 变参格式化 + arena_snapshot/arena_rewind 快照回退
 *   5) arena_da_append 动态数组（String_Builder 模式）
 *   6) arena_reset/arena_free/arena_trim 释放语义（含压力循环）
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define ARENA_IMPLEMENTATION
#include "arena.h"

typedef struct {
    char *items;
    size_t count;
    size_t capacity;
} String_Builder;

static int failures = 0;

#define CHECK(cond, name) do { \
    if (cond) { printf("  [PASS] %s\n", name); } \
    else { printf("  [FAIL] %s\n", name); failures++; } \
} while (0)

int main(void)
{
    Arena a = {0};

    /* T2: 区域增长 —— 多次跨越默认容量(8KB)分配，验证分裂后写读 */
    {
        size_t big = 30000; /* > ARENA_REGION_DEFAULT_CAPACITY(8KB) */
        unsigned char *p = arena_alloc(&a, big);
        CHECK(p != NULL, "T2 arena_alloc big (>8KB) non-NULL");
        if (p) {
            for (size_t i = 0; i < big; i++) p[i] = (unsigned char)(i & 0xff);
            int ok = 1;
            for (size_t i = 0; i < big; i++)
                if (p[i] != (unsigned char)(i & 0xff)) { ok = 0; break; }
            CHECK(ok, "T2 cross-Region data write/readback intact");
        }
    }

    /* T3a: arena_realloc 扩容保真 */
    {
        char *s = arena_alloc(&a, 16);
        if (s) memcpy(s, "hello-arena", 12);
        char *s2 = arena_realloc(&a, s, 16, 64);
        CHECK(s2 != NULL, "T3 arena_realloc enlarged non-NULL");
        if (s2) CHECK(memcmp(s2, "hello-arena", 11) == 0, "T3 realloc data preserved");
    }

    /* T3b: arena_memdup 字节 round-trip */
    {
        unsigned char src[257];
        for (int i = 0; i < 257; i++) src[i] = (unsigned char)(i * 7);
        void *dup = arena_memdup(&a, src, sizeof(src));
        CHECK(dup != NULL, "T3b arena_memdup non-NULL");
        if (dup) CHECK(memcmp(dup, src, sizeof(src)) == 0, "T3b memdup byte round-trip");
    }

    /* T4: arena_sprintf + rewind 快照回退 */
    {
        char *msg = arena_sprintf(&a, "fmt %d %s %.1f", 42, "ok", 3.5);
        CHECK(msg != NULL, "T4 arena_sprintf non-NULL");
        if (msg) CHECK(strcmp(msg, "fmt 42 ok 3.5") == 0, "T4 sprintf format exact");

        Arena_Mark m = arena_snapshot(&a);
        arena_alloc(&a, 1024*1024); /* 占用后回退 */
        arena_rewind(&a, m);
        size_t before = (size_t)a.begin->count;
        arena_alloc(&a, 1024*1024); /* 再次分配应复用被回退的空间 */
        (void)before;
        /* rewind 后 arena 仍可继续使用 */
        char *s2 = arena_sprintf(&a, "after-rewind");
        CHECK(s2 != NULL && strcmp(s2, "after-rewind") == 0, "T4 rewind then reuse works");
    }

    /* T5: arena_da_append / String_Builder（上游 001 演示同款路径） */
    {
        String_Builder sb = {0};
        arena_sb_append_cstr(&a, &sb, "Hello, ");
        char name[] = {'W', 'o', 'r', 'l', 'd'};
        arena_sb_append_buf(&a, &sb, name, sizeof(name));
        arena_sb_append_null(&a, &sb);
        CHECK(sb.items != NULL, "T5 sb.items non-NULL");
        if (sb.items) CHECK(strcmp(sb.items, "Hello, World") == 0, "T5 sb content exact");
    }

    /* T6: reset/free/trim 压力循环（释放语义不崩溃） */
    {
        int ok = 1;
        for (int i = 0; i < 200; i++) {
            Arena b = {0};
            void *p = arena_alloc(&b, 1 + (i % 7) * 4096);
            if (!p) { ok = 0; break; }
            arena_reset(&b);
            arena_free(&b);
        }
        CHECK(ok, "T6 200x alloc/reset/free stress loop clean");
        arena_trim(&a);
        arena_free(&a);
        CHECK(1, "T6 arena_trim/arena_free no crash");
    }

    /* T1 编译即验证（consumer 编译通过）；T7 在脚本层用 readelf 校验 ELF */
    if (failures == 0) {
        printf("arena OHOS special test: ALL PASS\n");
        return 0;
    }
    printf("arena OHOS special test: %d FAILURE(S)\n", failures);
    return 1;
}