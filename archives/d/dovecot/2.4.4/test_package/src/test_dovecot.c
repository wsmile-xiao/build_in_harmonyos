// test_dovecot.c — 消费者视角验证 dovecot 核心静态库（libdovecot.a）API，
// 覆盖被适配修改的核心路径：
//   1. pool/buffer 基础链路（mempool.c / buffer.c）
//   2. base64 encode/decode roundtrip（base64.c）
//   3. lib_init / lib_deinit 生命周期
// 断言口径见 ../MANIFEST.yml。
#include <dovecot/lib.h>
#include <dovecot/base64.h>
#include <dovecot/buffer.h>
#include <dovecot/mempool.h>

#include <stdio.h>
#include <string.h>

#define CHECK(cond) do { \
    if (!(cond)) { \
        fprintf(stderr, "FAIL: %s (line %d)\n", #cond, __LINE__); \
        return 1; \
    } \
} while (0)

int main(void)
{
    pool_t pool;
    buffer_t *enc, *dec;
    static const char msg[] = "dovecot/ohos base64 roundtrip \x01\x02\xff \xe6\xb5\x8b\xe8\xaf\x95";
    size_t used;

    lib_init();

    pool = pool_alloconly_create("test-dovecot", 128);

    /* 1. base64 encode（含 NUL 边界与 UTF-8 多字节） */
    enc = buffer_create_dynamic(pool, 128);
    base64_encode(msg, sizeof(msg) - 1, enc);
    used = buffer_get_used_size(enc);
    CHECK(used > 0);
    /* 输入首字节 0x64='d' 的前 6 bit=25 -> base64 字母表第 25 项='Z' */
    CHECK(((const unsigned char *)buffer_get_data(enc, NULL))[0] == 'Z');

    /* 2. decode 回原数据 */
    dec = buffer_create_dynamic(pool, 128);
    CHECK(base64_decode(buffer_get_data(enc, NULL), buffer_get_used_size(enc), dec) >= 0);
    CHECK(buffer_get_used_size(dec) == sizeof(msg) - 1);
    CHECK(memcmp(buffer_get_data(dec, NULL), msg, buffer_get_used_size(dec)) == 0);

    /* 3. 边界：空串（单次调用，避免冗余重复求值） */
    dec = buffer_create_dynamic(pool, 128);
    {
        int rc = base64_decode("", 0, dec);
        CHECK(rc == 0 || rc == 1);
    }
    CHECK(buffer_get_used_size(dec) == 0);

    buffer_free(&enc);
    buffer_free(&dec);
    pool_unref(&pool);
    lib_deinit();

    printf("test_dovecot: OK (base64 roundtrip, %zu bytes encoded)\n", used);
    return 0;
}
