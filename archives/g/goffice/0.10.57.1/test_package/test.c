/* test.c — goffice 0.10.57.1 L1 smoke test
 *
 * 通过 pkg-config 链接 libgoffice-0.10，实质调用公开 API 并断言：
 *   - libgoffice_init() / libgoffice_shutdown() 生命周期
 *   - goffice 版本宏
 *   - go_format_get_type() 类型注册（GObject 类型系统）
 *   - go_format_general() 构造器与 go_format_is_general() 语义
 *
 * 编译方式见 CMakeLists.txt（find_package(PkgConfig) + pkg_check_modules）。
 */
#include <stdio.h>
#include <string.h>

#include <goffice/goffice.h>
#include <goffice/utils/go-format.h>

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
    /* libgoffice_init() 返回 void，不能放进 TEST 的 if((expr)) 条件
     * （if((void)) 非法 C），先调用再断言其执行到此处。 */
    libgoffice_init();
    TEST("libgoffice_init", 1);

    /* goffice 版本宏：与上游 0.10.57 完全一致。 */
    TEST("GOFFICE_VERSION == \"0.10.57\"",
         g_strcmp0(GOFFICE_VERSION, "0.10.57") == 0);
    TEST("GO_VERSION_MAJOR == 10", GO_VERSION_MAJOR == 10);
    TEST("GO_VERSION_MINOR == 57", GO_VERSION_MINOR == 57);

    /* go_format_get_type()：init 后 _go_number_format_init() 已注册
     * GO_TYPE_FORMAT 类型，返回的 GType 必须非 0（0 为无效类型）。 */
    GType fmt_type = go_format_get_type();
    TEST("go_format_get_type() returns non-zero GType", fmt_type != 0);
    TEST("g_type_name(go_format_get_type()) is non-NULL",
         g_type_name(fmt_type) != NULL);

    /* go_format_general()：构造"通用"数字格式对象，应为非 NULL，
     * 且 go_format_is_general() 语义应返回 TRUE。 */
    GOFormat *fmt = go_format_general();
    TEST("go_format_general() returns non-NULL GOFormat", fmt != NULL);
    if (fmt != NULL) {
        TEST("go_format_is_general(go_format_general()) is TRUE",
             go_format_is_general(fmt));
        TEST("go_format_as_XL(go_format_general()) is non-NULL",
             go_format_as_XL(fmt) != NULL);
        go_format_unref(fmt);
    }

    libgoffice_shutdown();
    TEST("libgoffice_shutdown", 1);

    printf("\n=== Results: %d passed, %d failed ===\n", n_passed, n_failed);
    return n_failed > 0 ? 1 : 0;
}
