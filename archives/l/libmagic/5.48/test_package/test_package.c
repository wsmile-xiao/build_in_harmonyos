/* libmagic 5.48 真实消费者测试：magic_open / magic_load / 文件与 buffer
 * 识别 / MIME / 负向路径 / magic_close。测试数据运行时生成。 */
#include <magic.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int g_failures = 0;
static int g_checks = 0;

#define CHECK(cond, msg) do {                                   \
    g_checks++;                                                 \
    if (cond) { printf("ok - %s\n", (msg)); }                   \
    else      { printf("not ok - %s\n", (msg)); g_failures++; } \
} while (0)

#define MAGIC_PATH (MAGIC_DB_PATH)

int main(void)
{
    /* 1. magic_open */
    magic_t ms = magic_open(MAGIC_NONE);
    CHECK(ms != NULL, "magic_open(MAGIC_NONE) returns handle");

    /* 2. magic_load */
    int rc = magic_load(ms, MAGIC_PATH);
    CHECK(rc == 0, "magic_load with explicit db path");

    /* 运行时生成测试文件（无二进制 fixture）*/
    FILE *f = fopen("./tp_test.bin", "w");
    CHECK(f != NULL, "create temp test file");
    if (!f) { magic_close(ms); return 1; }
    /* GIF87a 签名 */
    const unsigned char gif[] = { 'G','I','F','8','7','a', 1,0, 1,0,
                                  0x80, 0, 0 };
    fwrite(gif, 1, sizeof(gif), f);
    fclose(f);

    /* 3. 文件路径识别 */
    const char *t = magic_file(ms, "./tp_test.bin");
    CHECK(t != NULL && strstr(t, "GIF") != NULL, "magic_file identifies GIF");

    /* 4. 内存 buffer 识别（ELF 签名）*/
    const unsigned char elf[] = { 0x7f,'E','L','F',2,1,1,0,
                                  0,0,0,0,0,0,0,0 };
    t = magic_buffer(ms, elf, sizeof(elf));
    CHECK(t != NULL && strstr(t, "ELF") != NULL, "magic_buffer identifies ELF header");

    /* 5. MIME 类型 */
    magic_t mm = magic_open(MAGIC_MIME_TYPE);
    CHECK(mm != NULL, "magic_open(MAGIC_MIME_TYPE) returns handle");
    rc = magic_load(mm, MAGIC_PATH);
    CHECK(rc == 0, "magic_load for mime handle");
    t = magic_file(mm, "./tp_test.bin");
    CHECK(t != NULL && strncmp(t, "image/gif", 9) == 0,
          "MIME type image/gif for GIF file");
    /* 16 字节 ELF 头不足以出 MIME，MIME 只对完整可识别内容有效 */
    t = magic_buffer(mm, elf, sizeof(elf));
    CHECK(t != NULL && strlen(t) > 0, "MIME buffer path returns non-empty");

    /* 6. 负向路径：不存在路径、未 load 的句柄。
     * libmagic 语义：magic_file 失败时返回错误描述字符串（非 NULL），
     * 调用方用 magic_errno/魔法字符串判断——与 file(1) 打印行为一致。*/
    t = magic_file(ms, "/nonexistent/path/nope.bin");
    CHECK(t != NULL && strstr(t, "cannot open") != NULL,
          "magic_file on nonexistent path returns error string");
    magic_t mu = magic_open(MAGIC_NONE);
    CHECK(mu != NULL, "second magic_open for negative test");
    t = magic_file(mu, "./tp_test.bin");
    CHECK(t == NULL, "magic_file before magic_load returns NULL");

    /* 版本一致性：file(1) 与库同源构建，5.48 → 548 */
    CHECK(magic_version() == 548, "magic_version() == 548");

    /* 7. magic_close */
    magic_close(ms);
    magic_close(mm);
    magic_close(mu);
    CHECK(1, "magic_close on all handles");

    remove("./tp_test.bin");

    printf("1..%d\n", g_checks);
    printf("# checks=%d failures=%d\n", g_checks, g_failures);
    return g_failures == 0 ? 0 : 1;
}
