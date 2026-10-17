/* test.c — gnumeric 1.12.57 L1 smoke test
 *
 * 通过 pkg-config 链接 libspreadsheet-1.12.57，实质调用公开 API 并断言：
 *   - gnumeric.h 的尺寸宏 (GNM_MAX_ROWS / GNM_MAX_COLS)
 *   - gnm_sys_lib_dir() / gnm_sys_data_dir() (gutils.h, 编译期路径)
 *   - gnm_app_get_type() (application.h, GObject 类型注册 → 证明 libspreadsheet 真实链接)
 *
 * 编译方式见 CMakeLists.txt（find_package(PkgConfig) + pkg_check_modules）。
 */
#include <stdio.h>
#include <string.h>

#include <glib.h>
#include <spreadsheet/gnumeric.h>
#include <spreadsheet/libgnumeric.h>
#include <spreadsheet/gutils.h>
#include <spreadsheet/application.h>

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
    /* gnumeric 库需要先初始化（gutils_init 设置 gnm_sys_lib_dir/data_dir 等
     * 编译期路径），否则 gnm_sys_lib_dir() 返回 NULL。 */
    gutils_init();

    /* gnumeric.h 编译期常量：与上游 1.12.57 完全一致。 */
    TEST("GNM_MAX_ROWS == 0x1000000", GNM_MAX_ROWS == 0x1000000);
    TEST("GNM_MAX_COLS == 0x4000", GNM_MAX_COLS == 0x4000);

    /* gutils.h: 编译进 libspreadsheet 的安装路径，应为非空字符串。 */
    const char *libdir = gnm_sys_lib_dir();
    TEST("gnm_sys_lib_dir() returns non-NULL", libdir != NULL);
    if (libdir != NULL)
        TEST("gnm_sys_lib_dir() returns non-empty", libdir[0] != '\0');

    const char *datadir = gnm_sys_data_dir();
    TEST("gnm_sys_data_dir() returns non-NULL", datadir != NULL);
    if (datadir != NULL)
        TEST("gnm_sys_data_dir() returns non-empty", datadir[0] != '\0');

    /* application.h: GObject 类型注册（G_DEFINE_TYPE 自动生成），
     * 返回非 0 GType 证明 libspreadsheet 的符号真实可链接。 */
    GType app_type = gnm_app_get_type();
    TEST("gnm_app_get_type() returns non-zero GType", app_type != 0);
    TEST("g_type_name(gnm_app_get_type()) is non-NULL",
         g_type_name(app_type) != NULL);

    printf("\n=== Results: %d passed, %d failed ===\n", n_passed, n_failed);
    return n_failed > 0 ? 1 : 0;
}
