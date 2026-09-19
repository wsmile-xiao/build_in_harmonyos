/* vstr 1.0.15 consumer-side verification (R34: 真实调用被测包 API)。
 *
 * 编译链接：<vstr.h> 头 + -lvstr 库。
 * 用例（3 个显式断言，与 test_package/conanfile.py 的 discovered=3 对应）：
 *   1. vstr_make_base() 返回非空 base 且初始 len==0
 *   2. vstr_add_cstr_buf() 追加 "Hello" 后 len==5、导出内容为 "Hello"
 *   3. 再追加 ", world!" 后 len==13、导出内容为 "Hello, world!"
 */
#include <vstr.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int failed = 0;

#define CHECK(cond) do { \
    if (!(cond)) { \
        fprintf(stderr, "FAIL (line %d): %s\n", __LINE__, #cond); \
        failed = 1; \
    } \
} while (0)

int main(void)
{
    struct Vstr_base *s = NULL;
    char *out = NULL;

    if (!vstr_init()) {
        fprintf(stderr, "vstr_init() failed\n");
        return EXIT_FAILURE;
    }

    /* 用例 1: 创建空 base */
    s = vstr_make_base(NULL);
    CHECK(s != NULL && s->len == 0);

    /* 用例 2: 追加 "Hello" */
    CHECK(vstr_add_cstr_buf(s, s->len, "Hello") != 0);
    CHECK(s->len == 5);
    out = vstr_export_cstr_malloc(s, 1, s->len);
    CHECK(out != NULL && strcmp(out, "Hello") == 0);
    free(out);

    /* 用例 3: 再追加 ", world!" */
    CHECK(vstr_add_cstr_buf(s, s->len, ", world!") != 0);
    CHECK(s->len == 13);
    out = vstr_export_cstr_malloc(s, 1, s->len);
    CHECK(out != NULL && strcmp(out, "Hello, world!") == 0);
    free(out);

    if (failed == 0)
        printf("vstr consumer test OK: \"Hello, world!\"\n");

    vstr_free_base(s);
    vstr_exit();

    return failed ? EXIT_FAILURE : EXIT_SUCCESS;
}
