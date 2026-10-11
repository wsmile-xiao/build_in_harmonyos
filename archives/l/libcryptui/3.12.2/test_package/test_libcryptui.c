/* libcryptui 3.12.2 消费者用例（HarmonyOS PC / OHOS，headless，TAP 输出）。
 *
 * 真实消费被测产物：
 *   1. 链接安装产物 libcryptui.so（SONAME libcryptui.so.0）；
 *   2. 包含安装后的公共头（并由构建脚本按上游要求定义
 *      LIBCRYPTUI_API_SUBJECT_TO_CHANGE，否则 cryptui.h 直接 #error）；
 *   3. 调用库内真实逻辑 cryptui_key_get_base()（截断第二个冒号之后的内容）；
 *   4. 走 GObject 类型系统验证 CryptUIKeyStore 注册及其父类 GtkTreeModelSort
 *      （同时验证 libcryptui ↔ gtk-3 ↔ dbus-glib 的链接完整性）。
 *
 * 刻意避开需要窗口系统或 DBus 会话总线的入口：cryptui_prompt_* 系列、
 * cryptui_key_store_new()（内部 g_settings_new 需要已编译的
 * org.gnome.seahorse.recipients schema）。HarmonyOS PC 无窗口系统，
 * 这些路径不可执行，属平台限制。
 */
#include <glib.h>
#include <gtk/gtk.h>

#include <cryptui.h>
#include <cryptui-key-store.h>

static int checks = 0;
static int failures = 0;

static void
check (gboolean condition, const gchar *what)
{
    checks++;
    if (condition) {
        g_print ("ok %d - %s\n", checks, what);
    } else {
        failures++;
        g_print ("not ok %d - %s\n", checks, what);
    }
}

static void
check_base (const gchar *key, const gchar *expected, const gchar *what)
{
    gchar *base = cryptui_key_get_base (key);
    check (base != NULL && g_strcmp0 (base, expected) == 0, what);
    g_free (base);
}

int
main (void)
{
    g_print ("# libcryptui consumer test (headless: no display, no session bus)\n");

    /* --- ABI 常量：CryptUIEncType / CryptUIKeyFlags / CryptUILocation /
     *     CryptUIValidity（cryptui.h 注释明确要求"Never ever change a value"） --- */
    check (CRYPTUI_ENCTYPE_SYMMETRIC == 1, "CRYPTUI_ENCTYPE_SYMMETRIC ABI value == 1");
    check (CRYPTUI_ENCTYPE_PRIVATE == 3, "CRYPTUI_ENCTYPE_PRIVATE ABI value == 3");
    check (CRYPTUI_FLAG_CAN_ENCRYPT == 0x00000002,
           "CRYPTUI_FLAG_CAN_ENCRYPT ABI bit == 0x00000002");
    check (CRYPTUI_FLAG_EXPORTABLE == 0x00100000,
           "CRYPTUI_FLAG_EXPORTABLE ABI bit == 0x00100000");
    check (CRYPTUI_LOC_LOCAL == 100, "CRYPTUI_LOC_LOCAL ABI value == 100");
    check (CRYPTUI_VALIDITY_REVOKED == -3, "CRYPTUI_VALIDITY_REVOKED ABI value == -3");

    /* --- 真实库逻辑：cryptui_key_get_base() --- */
    check_base ("1234567890ABCDEF", "1234567890ABCDEF",
                "cryptui_key_get_base() keeps a bare key unchanged");
    check_base ("sec:1234567890ABCDEF", "sec:1234567890ABCDEF",
                "cryptui_key_get_base() keeps a single-colon key intact");
    check_base ("org.gnome.seahorse:keys:1234567890ABCDEF", "org.gnome.seahorse:keys",
                "cryptui_key_get_base() strips everything after the second colon");
    check_base ("org.gnome.seahorse:keys:a:b:c", "org.gnome.seahorse:keys",
                "cryptui_key_get_base() handles keys with 4+ segments");
    check_base (":leading", ":leading",
                "cryptui_key_get_base() tolerates a leading colon (no second colon)");

    /* --- GObject 类型系统：CryptUIKeyStore : GtkTreeModelSort --- */
    check (CRYPTUI_TYPE_KEY_STORE != G_TYPE_INVALID,
           "CRYPTUI_TYPE_KEY_STORE is a registered GType");
    check (g_type_is_a (CRYPTUI_TYPE_KEY_STORE, GTK_TYPE_TREE_MODEL_SORT) == TRUE,
           "CryptUIKeyStore derives from GtkTreeModelSort (gtk-3 linkage)");
    check (g_type_is_a (CRYPTUI_TYPE_KEY_STORE, G_TYPE_OBJECT) == TRUE,
           "CryptUIKeyStore is a GObject-derived type");

    /* --- CryptUIKeyStore 列布局（cryptui-key-store.h 的公开 enum 契约） --- */
    check (CRYPTUI_KEY_STORE_NAME == 0 && CRYPTUI_KEY_STORE_KEY == 6,
           "CryptUIKeyStore column ABI: NAME == 0, KEY == 6");
    check (CRYPTUI_KEY_STORE_NCOLS == 7,
           "CryptUIKeyStore exposes 7 model columns (NCOLS == 7)");

    g_print ("1..%d\n", checks);
    if (failures > 0) {
        g_printerr ("# %d of %d checks FAILED\n", failures, checks);
        return 1;
    }
    g_print ("# all %d checks passed\n", checks);
    return 0;
}
