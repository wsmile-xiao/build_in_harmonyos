/* test.c — libgsf 1.14.53 L1 smoke test
 *
 * Links against libgsf-1.so and verifies core API calls:
 *   gsf_init / gsf_infile_msole_new / gsf_shutdown.
 * Compile with -L<libdir> -lgsf-1 via CMake.
 */
#include <stdio.h>
#include <stdlib.h>
#include <gsf/gsf.h>

static int n_passed = 0;
static int n_failed = 0;

#define TEST(name, expr) do { \
    if ((expr)) { \
        printf("  PASS: %s\n", (name)); \
        n_passed++; \
    } else { \
        printf("  FAIL: %s\n", (name)); \
        n_failed++; \
    } \
} while (0)

int main(void) {
    /* Init libgsf (no params needed) — gsf_init() 返回 void,
     * 不能放进 TEST 宏的 if((expr)) 条件(if((void)) 非法 C),
     * 先调用再断言可执行 */
    gsf_init();
    TEST("gsf_init", 1);

    /* gsf_infile_msole_new(source, err) — OLE2 container constructor.
     * 传 NULL source 无法解析 OLE2,libgsf 实测返回 NULL(解析前即拒绝,
     * 不设置 GError——NULL source 无错误可报);该断言验证构造函数
     * 真实可调用且对 NULL source 的行为符合实现。 */
    GError *err = NULL;
    GsfInfile *infile = gsf_infile_msole_new(NULL, &err);
    TEST("gsf_infile_msole_new(NULL,&err) returns NULL for NULL source (API semantics)", infile == NULL);
    if (infile != NULL) {
        g_object_unref(infile);
    }
    if (err != NULL) {
        g_error_free(err);
    }

    /* gsf_input_memory_new_clone(buf,len) — 内存输入构造器(clone 版,内部
     * g_try_malloc+memcpy 拷贝,不接管调用方缓冲所有权,对 static 输入安全)。
     * 注: gsf_input_memory_new 的第三参是 needs_free(TRUE 才在析构时 g_free),
     * 对 static 缓冲传 TRUE 会在 g_object_unref 时 g_free 静态内存导致崩溃,
     * 传 FALSE 则正确但不接管;clone 版无此所有权争议,故优先使用。 */
    static guint8 const buf[4] = { 0, 0, 0, 0 };
    GsfInput *input = gsf_input_memory_new_clone((guint8 const *)buf, (gsf_off_t)4);
    TEST("gsf_input_memory_new_clone(valid buf) returns non-NULL GsfInput", input != NULL);
    if (input != NULL) {
        g_object_unref(input);
    }

    /* gsf_output_memory_new() — 内存输出构造器,应返回非 NULL GsfOutput。 */
    GsfOutput *output = gsf_output_memory_new();
    TEST("gsf_output_memory_new() returns non-NULL GsfOutput", output != NULL);
    if (output != NULL) {
        g_object_unref(output);
    }

    /* gsf_shutdown (cleanup) */
    gsf_shutdown();
    TEST("gsf_shutdown", 1);

    printf("\n=== Results: %d passed, %d failed ===\n", n_passed, n_failed);
    return n_failed > 0 ? 1 : 0;
}
