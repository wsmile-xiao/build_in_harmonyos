/* test_ohos.c — libgda5/HarmonyOS 专项测试用例（≥1 项鸿蒙特有断言）
 *
 * 用例 1（平台守卫）：编译期强制 __OHOS__，非 OHOS 目标直接编译失败——
 *   保证本用例只在 HarmonyOS/aarch64 目标上生效，不会被误当成通用测试。
 * 用例 2（插件动态加载）：HarmonyOS 使用 musl + lld 链接，provider 是运行期
 *   dlopen 的 .so；用 dlopen(RTLD_NOW) 实际加载 provider 插件，验证鸿蒙
 *   动态加载器能从（HMDFS 上的）conan 包路径解析并完成重定位。
 * 用例 3（UTF-8 往返）：鸿蒙系统默认 UTF-8 locale，验证含中文/emoji 的多字节
 *   文本经 libgda → SQLite provider → 回读后字节完全一致。
 * 用例 4（文件型数据库）：HMDFS 上创建 SQLite 数据库文件、写入、关闭、重开并
 *   校验数据仍在，覆盖鸿蒙文件系统的文件 I/O 路径（E002 类陷阱：不使用 /tmp）。
 */
#if !defined(__OHOS__)
#error "test_ohos.c 是 HarmonyOS 专项测试，必须在 OHOS 目标上编译（__OHOS__ 未定义）"
#endif

#include <libgda/libgda.h>
#include <glib.h>
#include <dlfcn.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

static int failures = 0;

#define CHECK(cond, msg)                                     \
        do {                                                 \
                if (cond) {                                  \
                        printf("  ok   : %s\n", msg);        \
                } else {                                     \
                        printf("  FAIL : %s\n", msg);        \
                        failures++;                          \
                }                                            \
        } while (0)

int
main (void)
{
        GError *error = NULL;
        gda_init ();

        /* ---- 用例 2: provider 插件动态加载（dlopen） ---- */
        GdaProviderInfo *info = gda_config_get_provider_info ("SQLite");
        CHECK (info != NULL && info->location != NULL, "获取 SQLite provider 插件路径");
        if (info != NULL && info->location != NULL) {
                printf("       插件路径: %s\n", info->location);
                CHECK (g_file_test (info->location, G_FILE_TEST_IS_REGULAR),
                       "provider 插件文件存在于包路径下");
                void *handle = dlopen (info->location, RTLD_NOW | RTLD_LOCAL);
                if (handle == NULL) {
                        printf("       dlopen error: %s\n", dlerror ());
                }
                CHECK (handle != NULL, "dlopen(RTLD_NOW) 加载 provider 插件成功");
                if (handle != NULL) {
                        CHECK (dlsym (handle, "gda_provider_get_type") != NULL ||
                               dlsym (handle, "gda_sqlite_provider_get_type") != NULL ||
                               dlsym (handle, "gda_provider_sqlite_get_type") != NULL,
                               "插件导出 provider GType 符号");
                        dlclose (handle);
                }
        }

        /* ---- 用例 3: 中文/emoji UTF-8 往返（内存库） ---- */
        GdaConnection *cnc = gda_connection_open_from_string ("SQLite", "DB_DIR=.;DB_NAME=libgda5_ohos_l1_test", NULL,
                                                             GDA_CONNECTION_OPTIONS_NONE,
                                                             &error);
        CHECK (cnc != NULL, "打开 SQLite 文件库连接（UTF-8 往返前置）");
        if (cnc != NULL) {
                const gchar *zh = "鸿蒙 PC 平台适配测试 ⚡";
                gchar *sql = g_strdup_printf ("CREATE TABLE u (k integer, v text)");
                gda_connection_execute_non_select_command (cnc, sql, &error);
                g_free (sql);
                sql = g_strdup_printf ("INSERT INTO u VALUES (1, '%s')", zh);
                CHECK (gda_connection_execute_non_select_command (cnc, sql, &error) != -1,
                       "写入含中文/emoji 的 UTF-8 文本");
                g_free (sql);
                GdaDataModel *model = gda_connection_execute_select_command (cnc,
                                "SELECT v FROM u WHERE k = 1", &error);
                if (model != NULL && gda_data_model_get_n_rows (model) == 1) {
                        const GValue *v = gda_data_model_get_value_at (model, 0, 0, &error);
                        gchar *out = gda_value_stringify (v);
                        CHECK (out != NULL && strcmp (out, zh) == 0,
                               "UTF-8 多字节文本 round-trip 字节一致");
                        if (out != NULL && strcmp (out, zh) != 0) {
                                printf("       期望: %s\n       实际: %s\n", zh, out);
                        }
                        g_free (out);
                } else {
                        CHECK (FALSE, "UTF-8 往返查询返回 1 行");
                }
                gda_connection_close (cnc);
                g_object_unref (cnc);
        }

        /* ---- 用例 4: 文件型数据库（HMDFS 工作目录，不用 /tmp） ---- */
        gchar *db_path = g_strdup_printf ("%s/libgda5_ohos_file.db", g_get_current_dir ());
        g_unlink (db_path);
        gchar *cnc_string = g_strdup_printf ("DB_DIR=%s;DB_NAME=libgda5_ohos_file",
                                             g_get_current_dir ());

        GdaConnection *fc = gda_connection_open_from_string ("SQLite", cnc_string, NULL,
                                                            GDA_CONNECTION_OPTIONS_NONE,
                                                            &error);
        CHECK (fc != NULL, "在 HMDFS 工作目录打开文件型 SQLite 数据库");
        if (fc != NULL) {
                CHECK (gda_connection_execute_non_select_command (fc,
                               "CREATE TABLE p (n integer)", &error) != -1, "文件库建表");
                CHECK (gda_connection_execute_non_select_command (fc,
                               "INSERT INTO p VALUES (42)", &error) != -1, "文件库写入");
                gda_connection_close (fc);
                g_object_unref (fc);
                CHECK (g_file_test (db_path, G_FILE_TEST_IS_REGULAR),
                       "数据库文件已落盘（HMDFS 文件 I/O）");

                error = NULL;
                GdaConnection *fc2 = gda_connection_open_from_string ("SQLite", cnc_string,
                                NULL, GDA_CONNECTION_OPTIONS_NONE, &error);
                CHECK (fc2 != NULL, "重新打开已存在的数据库文件");
                if (fc2 != NULL) {
                        GdaDataModel *m = gda_connection_execute_select_command (fc2,
                                        "SELECT n FROM p", &error);
                        if (m != NULL && gda_data_model_get_n_rows (m) == 1) {
                                const GValue *val = gda_data_model_get_value_at (m, 0, 0, &error);
                                gchar *txt = gda_value_stringify ((GValue *) val);
                                CHECK (txt != NULL && strcmp (txt, "42") == 0,
                                       "重开后数据仍在（n == 42）");
                                g_free (txt);
                        } else {
                                CHECK (FALSE, "重开后查询返回 1 行");
                        }
                        gda_connection_close (fc2);
                        g_object_unref (fc2);
                }
                g_unlink (db_path);
        } else {
                printf("       error: %s\n", error ? error->message : "(no error)");
        }

        g_free (cnc_string);
        g_free (db_path);

        if (failures != 0) {
                printf ("test_ohos: %d 项失败\n", failures);
                return 1;
        }
        printf ("test_ohos: ALL PASS (HarmonyOS 专项)\n");
        return 0;
}
