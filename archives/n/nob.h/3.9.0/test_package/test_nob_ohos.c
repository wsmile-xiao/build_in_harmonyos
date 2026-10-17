#include <stdio.h>
#include <string.h>

/* 鸿蒙专项测试：在 OHOS(aarch64) 工具链下验证 nob.h 的内存与字符串
 * 不变量、边界行为，与上游快照对照测试互补——本测试不做任何快照，
 * 而是断言库 API 在 OHOS libc 上的确定性质。
 */
#define NOB_IMPLEMENTATION
#include <nob.h>

typedef struct {
    int *items;
    size_t count;
    size_t capacity;
} Numbers;

static int failures = 0;

#define CHECK(cond, msg) do { \
    if (!(cond)) { \
        fprintf(stderr, "FAIL: %s\n", msg); \
        failures++; \
    } else { \
        printf("PASS: %s\n", msg); \
    } \
} while (0)

int main(void) {
    /* 1) da 基础语义：append 后 count/capacity 不变式；resize 设置 count 并预留容量 */
    Numbers xs = {0};
    for (int i = 0; i < 5; ++i) nob_da_append(&xs, i * 2);
    CHECK(xs.count == 5 && xs.items[0] == 0 && xs.items[4] == 8,
          "da_append keeps count/in-order invariant");
    CHECK(xs.capacity >= xs.count, "da capacity covers count after append");

    /* 1b) da_resize：将数组调整为 new_size 个元素（count=64），容量充足 */
    nob_da_resize(&xs, 64);
    CHECK(xs.count == 64 && xs.capacity >= 64, "da_resize sets count and reserves capacity");
    xs.items[10] = 42;
    CHECK(xs.items[10] == 42, "da_resize backing storage is writable/readable");

    /* 2) temp 分配器：写入后立即可读，temp_reset 后循环复用（OHOS 上栈/堆行为） */
    char *first = nob_temp_sprintf("temp-%d", 7);
    CHECK(strcmp(first, "temp-7") == 0, "temp_sprintf returns readable string");
    for (int i = 0; i < 1000; ++i) {
        char *s = nob_temp_sprintf("loop-%d", i);
        CHECK(strncmp(s, "loop-", 5) == 0, "temp_sprintf loop allocation ok");
    }

    /* 3) String_View 边界：空串、trim、前缀匹配 */
    Nob_String_View empty = nob_sv_from_cstr("");
    CHECK(empty.count == 0, "sv_from_cstr(\"\") has zero count");
    Nob_String_View ws = nob_sv_from_cstr("  \t x  ");
    Nob_String_View tws = nob_sv_trim(ws);
    CHECK(tws.count == 1 && tws.data[0] == 'x', "sv_trim removes leading/trailing whitespace");
    Nob_String_View full = nob_sv_from_cstr("OHOS_arm64");
    CHECK(nob_sv_starts_with(full, nob_sv_from_cstr("OHOS")),
          "sv_starts_with prefix match on OHOS tag");

    /* 4) UTF-8 长度：ASCII 与多字节序列（OHOS 上标准 libc UTF-8 语义） */
    Nob_String_View utf8 = nob_sv_from_cstr("héllo");
    size_t overrun = 0;
    size_t len = nob_sv_utf8_len(utf8, &overrun);
    CHECK(len == 5, "sv_utf8_len counts codepoints not bytes");

    printf("ohos-special result: %s\n", failures == 0 ? "ALL PASS" : "FAILED");
    return failures;
}
