/* 消费者测试：真实调用 c-shquote 的 quote/unquote API。
 * 断言与上游 src/test-basic.c 的 test_quote/test_unquote 同款行为。
 */
#include <string.h>
#include <c-shquote.h>

int main(void) {
    char buf[64];
    char *out = buf;
    size_t n_out = sizeof(buf);

    /* 引号包裹："a" -> 'a'（3 字节，与上游 test_quote 断言一致） */
    if (c_shquote_quote(&out, &n_out, "a", 1) != 0) {
        return 1;
    }
    if (out != buf + 3 || memcmp(buf, "'a'", 3) != 0) {
        return 2;
    }

    /* 去引号：'a b' -> a b（空格被单引号保护） */
    const char *src = "'a b'";
    out = buf;
    n_out = sizeof(buf);
    if (c_shquote_unquote(&out, &n_out, src, strlen(src)) != 0) {
        return 3;
    }
    if (out != buf + 3 || memcmp(buf, "a b", 3) != 0) {
        return 4;
    }

    return 0;
}
