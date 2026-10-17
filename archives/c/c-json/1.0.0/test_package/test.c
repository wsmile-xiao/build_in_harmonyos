/* 消费者测试：真实调用 c-json reader API。验证：字符串转义与 \uXXXX 解码、
 * 数字词法边界、非法输入的错误传播。
 * 注意：conan test_package 以 -DNDEBUG 编译，故使用显式返回码检查而非 assert()，
 * 确保 API 调用不被预处理移除。
 */
#include <stdlib.h>
#include <string.h>
#include <c-json.h>

/* 解码 JSON 字符串并与期望值比较（expect 为 C 字节串） */
static int check_string(const char *in, const char *expect, size_t n_expect) {
        CJsonReader *r = NULL;
        char *s = NULL;
        size_t n = 0;

        if (c_json_reader_new(&r, 256))
                return 1;
        c_json_reader_begin_read(r, in);
        if (c_json_reader_read_string(r, &s))
                return 2;
        if (!s || strlen(s) != n_expect || memcmp(s, expect, n_expect)) {
                free(s);
                return 3;
        }
        free(s);
        if (c_json_reader_end_read(r))
                return 4;
        c_json_reader_free(r);
        return 0;
}

/* 数字词法：reader 返回指向输入内部的指针与长度 */
static int check_number(const char *in, const char *expect, size_t n_expect) {
        CJsonReader *r = NULL;
        const char *number = NULL;
        size_t n_number = 0;

        if (c_json_reader_new(&r, 256))
                return 1;
        c_json_reader_begin_read(r, in);
        if (c_json_reader_read_number(r, &number, &n_number))
                return 2;
        if (!number || n_number != n_expect || memcmp(number, expect, n_expect))
                return 3;
        if (c_json_reader_end_read(r))
                return 4;
        c_json_reader_free(r);
        return 0;
}

/* 非字符串输入必须报 C_JSON_E_INVALID_TYPE */
static int check_invalid_type(const char *in) {
        CJsonReader *r = NULL;
        char *s = NULL;
        int res;

        if (c_json_reader_new(&r, 256))
                return 1;
        c_json_reader_begin_read(r, in);
        res = c_json_reader_read_string(r, &s);
        c_json_reader_free(r);
        return res == C_JSON_E_INVALID_TYPE ? 0 : 5;
}

int main(void) {
        /* 1) 转义 \n 解码为真实换行字节 0x0a */
        if (check_string("\"a\\nb\"", "a\nb", 3))
                return 1;

        /* 2) \u00e4 解码为 UTF-8 两字节序列 C3 A4（U+00E4） */
        if (check_string("\"\\u00e4\"", "\xc3\xa4", 2))
                return 2;

        /* 3) 数字词法边界：-3.14 长度 5 */
        if (check_number("-3.14", "-3.14", 5))
                return 3;

        /* 4) 非字符串输入的错误传播 */
        if (check_invalid_type("123"))
                return 4;

        return 0;
}
