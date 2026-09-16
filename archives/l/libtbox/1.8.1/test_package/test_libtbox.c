/*
 * test_libtbox.c — libtbox 1.8.1 真实调用测试
 *
 * 真实调用 libtbox 公共 API（R34，非空壳）：
 *   - tb_init(tb_null, tb_null) / tb_exit()：库初始化与退出
 *   - tb_crc32_make(): tbox-variant KAT ("123456789"/seed0 -> 0x7F89A189)
 *   - tb_crc32_make()：空输入、确定性、区分性
 *   - tb_vector_*：字符串 vector 插入、长度、内容遍历比对
 *
 * 退出码 0 = 全部断言通过；非 0 = 失败。
 */
#include <stdio.h>
#include <string.h>
#include <tbox/tbox.h>

static int failures = 0;

#define CHECK(cond, msg)                                 \
    do {                                                 \
        if (!(cond)) {                                   \
            printf("FAIL: %s\n", (msg));                 \
            failures++;                                  \
        } else {                                         \
            printf("PASS: %s\n", (msg));                 \
        }                                                \
    } while (0)

int main(void)
{
    /* 1. 库初始化（失败则后续全部无意义，直接退出） */
    CHECK(tb_init(tb_null, tb_null) == tb_true, "tb_init() succeeds");
    if (failures != 0) {
        printf("INIT FAILED, abort\n");
        return 1;
    }

    /* 2. CRC32 已知答案向量（tbox 变体，非标准 IEEE 初值/异或）。
     * tbox 的 tb_crc32_make(seed) 直接以 seed 为迭代初值、无终异或，
     * seed=0 时 "123456789"(9B) = 0x7F89A189（以 g_crc32_table 复算），
     * 而非 binascii 标准值 0xCBF43926（初值 FFFFFFFF+终异或）。 */
    {
        static tb_byte_t const data[] = "123456789";
        tb_uint32_t crc = tb_crc32_make(data, 9, 0);
        printf("crc123456789=0x%08x\n", (unsigned)crc);
        CHECK(crc == 0x7F89A189u, "tb_crc32_make(\"123456789\") == 0x7F89A189");
    }

    /* 3. 空输入 CRC 为 0 */
    {
        tb_uint32_t crc = tb_crc32_make((tb_byte_t const *)"", 0, 0);
        CHECK(crc == 0, "tb_crc32_make(empty) == 0");
    }

    /* 4. 确定性：同一输入两次结果一致 */
    {
        tb_uint32_t a = tb_crc32_make_from_cstr("hello tbox", 0);
        tb_uint32_t b = tb_crc32_make_from_cstr("hello tbox", 0);
        printf("crc_hello_tbox=0x%08x 0x%08x\n", (unsigned)a, (unsigned)b);
        CHECK(a == b && a != 0, "tb_crc32_make_from_cstr() is deterministic and non-zero");
    }

    /* 5. 区分性：不同输入结果不同 */
    {
        tb_uint32_t a = tb_crc32_make_from_cstr("hello", 0);
        tb_uint32_t b = tb_crc32_make_from_cstr("tbox", 0);
        CHECK(a != b, "tb_crc32_make_from_cstr() differs across inputs");
    }

    /* 6. vector：插入 + 长度 + 内容 */
    {
        tb_vector_ref_t vector = tb_vector_init(0, tb_element_str(tb_true));
        CHECK(vector != tb_null, "tb_vector_init() returns non-null vector");
        if (vector != tb_null) {
            tb_vector_insert_tail(vector, "hello");
            tb_vector_insert_tail(vector, "tbox");
            CHECK(tb_vector_size(vector) == 2, "tb_vector_size() == 2 after two inserts");

            tb_char_t const *expected[] = {"hello", "tbox"};
            tb_size_t index = 0;
            tb_bool_t content_ok = tb_true;
            tb_for_all(tb_char_t const *, cstr, vector) {
                if (index >= 2 || cstr == tb_null || strcmp(cstr, expected[index]) != 0)
                    content_ok = tb_false;
                index++;
            }
            CHECK(content_ok == tb_true && index == 2, "tb_vector content matches insertion order");
            tb_vector_exit(vector);
        }
    }

    tb_exit();

    if (failures == 0) {
        printf("ALL TESTS PASSED\n");
        return 0;
    }
    printf("%d TEST(S) FAILED\n", failures);
    return 1;
}
