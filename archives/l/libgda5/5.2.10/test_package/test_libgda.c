/* test_libgda.c — libgda5 消费者功能测试（真实 API + 真实 SQL 往返）
 *
 * 覆盖：provider 注册发现 → 打开内存 SQLite 连接 → DDL/DML/DQL 往返 →
 *       数据模型随机访问（值级校验）。全部通过 libgda 公开 API 完成，
 *       不使用任何 stub 或打印占位（R34）。
 */
#include <libgda/libgda.h>
#include <glib.h>
#include <stdio.h>
#include <string.h>

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

        /* 1. provider 注册发现（配置管理器 + provider 插件目录） */
        GdaProviderInfo *info = gda_config_get_provider_info ("SQLite");
        CHECK (info != NULL, "SQLite provider 已注册（gda_config_get_provider_info）");
        if (info != NULL) {
                printf("       provider id       : %s\n", info->id);
                printf("       provider location : %s\n",
                        info->location ? info->location : "()");
                CHECK (info->location != NULL, "SQLite provider 有插件路径（location）");
        }

        GdaDataModel *providers = gda_config_list_providers ();
        CHECK (providers != NULL && gda_data_model_get_n_rows (providers) > 0,
               "gda_config_list_providers 至少返回 1 个 provider");

        /* 2. 打开内存数据库连接 */
        GdaConnection *cnc = gda_connection_open_from_string ("SQLite", "DB_DIR=.;DB_NAME=libgda5_l1_test", NULL,
                                                             GDA_CONNECTION_OPTIONS_NONE,
                                                             &error);
        CHECK (cnc != NULL, "打开 SQLite 文件库连接（DB_DIR=.;DB_NAME=libgda5_l1_test）");
        if (cnc == NULL) {
                printf("       error: %s\n", error ? error->message : "(no error)");
                return 1;
        }

        /* 3. DDL + DML */
        gint rc = gda_connection_execute_non_select_command (cnc,
                        "CREATE TABLE t (id integer, name text)", &error);
        CHECK (rc != -1, "CREATE TABLE t (id integer, name text)");
        rc = gda_connection_execute_non_select_command (cnc,
                        "INSERT INTO t VALUES (1, 'libgda5'), (2, 'ohos')", &error);
        CHECK (rc != -1, "INSERT 2 行");

        /* 4. DQL + 值级校验（随机访问数据模型） */
        GdaDataModel *model = gda_connection_execute_select_command (cnc,
                        "SELECT id, name FROM t ORDER BY id", &error);
        CHECK (model != NULL, "SELECT id, name FROM t");
        if (model != NULL) {
                CHECK (gda_data_model_get_n_rows (model) == 2, "SELECT 返回 2 行");
                CHECK (gda_data_model_get_n_columns (model) == 2, "SELECT 返回 2 列");
                if (gda_data_model_get_n_rows (model) == 2) {
                        const GValue *v_id = gda_data_model_get_value_at (model, 0, 0, &error);
                        const GValue *v_nm = gda_data_model_get_value_at (model, 1, 0, &error);
                        gchar *nm = gda_value_stringify (v_nm);
                        gchar *id = gda_value_stringify ((GValue *) v_id);
                        CHECK (id != NULL && strcmp (id, "1") == 0, "第 1 行 id == 1");
                        CHECK (nm != NULL && strcmp (nm, "libgda5") == 0,
                               "第 1 行 name == 'libgda5'");
                        g_free (id);
                        g_free (nm);
                }
        }

        /* 5. 清理 */
        gda_connection_close (cnc);
        g_object_unref (cnc);

        if (failures != 0) {
                printf ("test_libgda: %d 项失败\n", failures);
                return 1;
        }
        printf ("test_libgda: ALL PASS\n");
        return 0;
}
