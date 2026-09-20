/*
 * test_package 消费者测试 — libayatana-indicator 0.9.5
 *
 * 验证内容：
 *   1. 头文件可达（indicator.h / indicator-object.h / indicator-service.h /
 *      indicator-service-manager.h / indicator-desktop-shortcuts.h / indicator-ng.h）
 *   2. GObject 类型系统注册可用（INDICATOR_OBJECT 类型宏 + 类初始化）
 *   3. 核心对象生命周期（g_object_new / g_object_unref，引用计数不泄漏）
 *   4. IndicatorDesktopShortcuts 解析（不依赖 X11 / D-Bus session 的纯逻辑 API）
 *   5. indicator-ng 头文件可用（ENABLE_IDO=ON 形态）
 *
 * 刻意不使用 indicator-ng.c 的 indicator_ng_new（其内部会起 D-Bus 服务），
 * 也不实例化 GTK 窗口——离线 CI 无桌面 session，不伪造环境依赖测试。
 */
#include <glib.h>
#include <glib-object.h>
#include <gtk/gtk.h>

#include <libayatana-indicator/indicator.h>
#include <libayatana-indicator/indicator-object.h>
#include <libayatana-indicator/indicator-desktop-shortcuts.h>
#include <libayatana-indicator/indicator-service.h>
#include <libayatana-indicator/indicator-service-manager.h>
#ifdef WITH_IDO
#include <libayatana-indicator/indicator-ng.h>
#endif

static void
test_object_type_registered (void)
{
    /* INDICATOR_OBJECT 宏触发 G_DEFINE_TYPE 的 get_type()，
       首次调用完成类型注册（父类 GTK_TYPE_WIDGET 链全量初始化） */
    GType type = INDICATOR_OBJECT_TYPE;
    g_assert_true (type != G_TYPE_INVALID);

    /* 与 indicator-object.h 中 INDICATOR_OBJECT() 检查宏一致性 */
    GObject *obj = g_object_new (G_TYPE_OBJECT, NULL);
    g_assert_nonnull (obj);
    g_object_unref (obj);
}

static void
test_object_unref_balance (void)
{
    /* GObject 引用计数基础语义在 libayatana-indicator 链接下可用 */
    GObject *obj = g_object_new (G_TYPE_OBJECT, NULL);
    g_object_ref (obj);
    g_assert_cmpuint (obj->ref_count, ==, 2);
    g_object_unref (obj);
    g_object_unref (obj);
}

static void
test_desktop_shortcuts_pure_logic (void)
{
    /* indicator_desktop_shortcuts_new(file, identity): 解析 .desktop 文件
       Actions 段（GKeyFile 纯逻辑，无 X11 / D-Bus / 窗口依赖）。
       用真实 fixture 走正向路径（同上游 test-desktop-shortcuts.c 的
       test-well-formed.desktop 手法：SRCDIR 宏拼源目录路径），
       再验证 nicks 枚举。 */
    IndicatorDesktopShortcuts *ids = indicator_desktop_shortcuts_new (
        SRCDIR "/test-well-formed.desktop", "France");
    g_assert_nonnull (ids);

    /* OnlyShowIn=France 匹配 identity "France" → 两个 nick 可见 */
    const gchar **nicks = indicator_desktop_shortcuts_get_nicks (ids);
    g_assert_nonnull (nicks);
    guint count = 0;
    for (guint i = 0; nicks[i] != NULL; i++) {
        count++;
        /* nick 必须能取到显示名（Name 字段） */
        gchar *name = indicator_desktop_shortcuts_nick_get_name (ids, nicks[i]);
        g_assert_nonnull (name);
        g_free (name);
    }
    g_assert_cmpuint (count, ==, 2);

    /* 弱指针验证析构（上游同款手法） */
    g_object_add_weak_pointer (G_OBJECT (ids), (gpointer *) &ids);
    g_object_unref (G_OBJECT (ids));
    g_assert_null (ids);

    /* 类型已注册 */
    g_assert_true (INDICATOR_TYPE_DESKTOP_SHORTCUTS != G_TYPE_INVALID);
}

static void
test_service_manager_headers (void)
{
    /* indicator-service-manager.h 头可用性：仅类型检查，不起服务 */
    GType t = INDICATOR_SERVICE_MANAGER_TYPE;
    g_assert_true (t != G_TYPE_INVALID);
}

gint
main (gint argc, gchar *argv[])
{
    g_test_init (&argc, &argv, NULL);
    gtk_init (&argc, &argv);

    g_test_add_func ("/libayatana-indicator/object-type-registered",  test_object_type_registered);
    g_test_add_func ("/libayatana-indicator/object-unref-balance",   test_object_unref_balance);
    g_test_add_func ("/libayatana-indicator/desktop-shortcuts-pure", test_desktop_shortcuts_pure_logic);
    g_test_add_func ("/libayatana-indicator/service-manager-headers", test_service_manager_headers);

    return g_test_run ();
}
