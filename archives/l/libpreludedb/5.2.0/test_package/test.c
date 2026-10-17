/*
 * libpreludedb 5.2.0 消费者冒烟测试（Conan test_package / L1）。
 *
 * 只使用 libpreludedb 的公开 API，验证：
 *   1. 头文件布局与链接（#include <preludedb.h> + 链上 libpreludedb.so）
 *   2. 版本一致性：LIBPRELUDEDB_VERSION 宏、preludedb_check_version() 的
 *      「等于/高于当前版本接受、高于当前版本拒绝」语义
 *   3. 路径选择解析：preludedb_selected_path_new_string() 真正走到
 *      lex/yacc 生成的解析器（上游 src/preludedb-path-selection-parser.*）
 *   4. 与 libprelude 的依赖链：idmef_message_t 对象树可用（libpreludedb.so 的
 *      DT_NEEDED 能在 OHOS 上被加载）
 * 任何一条不满足都以非 0 退出，让 conan create / CI 直接失败。
 */
#include <stdio.h>
#include <string.h>

#include <libprelude/idmef.h>
#include <preludedb.h>
#include <preludedb-path-selection.h>
#include <preludedb-version.h>

static int failures;

#define CHECK(cond, ...)                                                       \
        do {                                                                   \
                if (!(cond)) {                                                 \
                        failures++;                                            \
                        fprintf(stderr, "FAIL " __VA_ARGS__);                  \
                        fprintf(stderr, "  [%s:%d]\n", __FILE__, __LINE__);    \
                }                                                              \
        } while (0)

static void test_version(void)
{
        CHECK(strcmp(LIBPRELUDEDB_VERSION, "5.2.0") == 0,
              "LIBPRELUDEDB_VERSION = %s", LIBPRELUDEDB_VERSION);
        CHECK(LIBPRELUDEDB_MAJOR_VERSION == 5 && LIBPRELUDEDB_MINOR_VERSION == 2,
              "version macros = %d.%d", LIBPRELUDEDB_MAJOR_VERSION,
              LIBPRELUDEDB_MINOR_VERSION);
        CHECK(preludedb_check_version(NULL) != NULL, "preludedb_check_version(NULL)");
        CHECK(preludedb_check_version("5.2.0") != NULL,
              "preludedb_check_version(5.2.0)");
        CHECK(preludedb_check_version("5.0.0") != NULL,
              "preludedb_check_version(5.0.0)");
        /* 高于当前库版本必须被拒绝，否则版本校验形同虚设 */
        CHECK(preludedb_check_version("99.0.0") == NULL,
              "preludedb_check_version(99.0.0) should return NULL");
}

static void test_path_selection(void)
{
        preludedb_selected_path_t *path = NULL;

        CHECK(preludedb_selected_path_new_string(
                      &path, "alert.source(0).node.address(0).address") == 0,
              "preludedb_selected_path_new_string");
        if (path == NULL) {
                return;
        }
        CHECK(preludedb_selected_path_get_object(path) != NULL,
              "selected path carries no object");
        CHECK(preludedb_selected_path_get_column_count(path) >= 1,
              "selected path column count = %u",
              preludedb_selected_path_get_column_count(path));
        preludedb_selected_path_destroy(path);

        /* 非法路径必须报错返回，而不是被静默接受 */
        path = NULL;
        CHECK(preludedb_selected_path_new_string(&path, "not-an-idmef-path((") < 0,
              "invalid path was accepted");
}

static void test_libprelude_linkage(void)
{
        idmef_message_t *message = NULL;

        CHECK(idmef_message_new(&message) == 0, "idmef_message_new (libprelude)");
        if (message != NULL) {
                CHECK(idmef_message_get_alert(message) == NULL,
                      "fresh idmef message unexpectedly has an alert");
                idmef_message_destroy(message);
        }
}

int main(void)
{
        test_version();
        test_path_selection();
        test_libprelude_linkage();

        if (failures != 0) {
                fprintf(stderr, "libpreludedb consumer test: %d assertion(s) failed\n",
                        failures);
                return 1;
        }
        printf("libpreludedb %s consumer test: OK\n", LIBPRELUDEDB_VERSION);
        return 0;
}
