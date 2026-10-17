/* //////////////////////////////////////////////////////////////////////////////////////
 * test_package/test.c — tbox 1.8.1 消费者验证
 *
 * 真实消费者视角：只 include 已安装的 <tbox/tbox.h>，链接被测 libtbox.a，
 * 逐项断言产物自报的版本号与 hash / utils / charset / container 模块行为。
 */
#include "tbox/tbox.h"

#include <stdio.h>
#include <string.h>

static int g_pass = 0;
static int g_fail = 0;

#define CHECK(cond, msg)                                                      \
    do {                                                                      \
        if (cond) { g_pass++; printf("  [PASS] %s\n", (msg)); }               \
        else      { g_fail++; printf("  [FAIL] %s\n", (msg)); }               \
    } while (0)

int main(void)
{
    printf("tbox 1.8.1 consumer test\n");

    if (!tb_init(tb_null, tb_null)) { printf("  [FAIL] tb_init\n"); return 1; }
    CHECK(1, "tb_init()");

    /* 1) 版本自证：被测产物自报 1.8.1（数值来自已安装的 tbox/tbox.config.h） */
    printf("  version = %d.%d.%d\n", TB_VERSION_MAJOR, TB_VERSION_MINOR, TB_VERSION_ALTER);
    CHECK(TB_VERSION_MAJOR == 1 && TB_VERSION_MINOR == 8 && TB_VERSION_ALTER == 1,
          "installed TB_VERSION_* == 1.8.1");

    /* 2) hash 模块：md5 */
    tb_byte_t digest[16] = {0};
    tb_size_t dn = tb_md5_make((tb_byte_t const*)"tbox", 4, digest, 16);
    tb_char_t hex[33] = {0};
    tb_size_t i = 0;
    for (i = 0; i < 16; ++i) tb_snprintf(hex + (i << 1), 3, "%02x", digest[i]);
    CHECK(dn == 16, "tb_md5_make() returns 16 bytes");
    CHECK(strcmp(hex, "a72d1c0c62bfe39ccd24e497c71c7e46") == 0, "md5(\"tbox\") digest matches");

    /* 3) utils 模块：base64 往返 */
    tb_char_t b64[64] = {0};
    tb_size_t bn = tb_base64_encode((tb_byte_t const*)"tbox", 4, b64, sizeof(b64));
    CHECK(bn == 8 && strcmp(b64, "dGJveA==") == 0, "base64 encode(\"tbox\") == dGJveA==");

    tb_byte_t raw[64] = {0};
    tb_size_t rn = tb_base64_decode(b64, bn, raw, sizeof(raw));
    CHECK(rn == 4 && memcmp(raw, "tbox", 4) == 0, "base64 decode round-trip");

    /* 4) charset 模块：UTF-8 <-> GB2312 往返（2 个汉字 = 3+3 / 2+2 字节） */
    tb_byte_t const* zh = (tb_byte_t const*)"\xe9\xb8\xbf\xe8\x92\x99"; /* 鸿蒙 */
    tb_byte_t gb[64] = {0};
    tb_byte_t back[64] = {0};
    tb_long_t gn = tb_charset_conv_data(tb_charset_type("utf8"), tb_charset_type("gb2312"),
                                        zh, 6, gb, sizeof(gb));
    CHECK(gn == 4, "utf8->gb2312: 2 个汉字 = 4 字节");
    tb_long_t zn = 0;
    if (gn == 4)
        zn = tb_charset_conv_data(tb_charset_type("gb2312"), tb_charset_type("utf8"),
                                  gb, (tb_size_t)gn, back, sizeof(back));
    CHECK(zn == 6 && memcmp(back, zh, 6) == 0, "gb2312->utf8 round-trip");

    /* 5) container + string 模块 */
    tb_vector_ref_t vec = tb_vector_init(0, tb_element_str(tb_true));
    CHECK(vec != tb_null, "tb_vector_init()");
    if (vec)
    {
        tb_vector_insert_tail(vec, "harmony");
        tb_vector_insert_tail(vec, "os");
        CHECK(tb_vector_size(vec) == 2, "vector size == 2");
        tb_vector_exit(vec);
    }

    tb_exit();
    printf("consumer assertions: %d passed, %d failed\n", g_pass, g_fail);
    return g_fail == 0 ? 0 : 1;
}
