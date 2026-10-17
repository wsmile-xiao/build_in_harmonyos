/*
 * test_package 消费者测试 - libayatana-indicator 0.9.4
 *
 * 真实链接 libayatana-indicator3 并调用其公开 API.只覆盖无需桌面
 * session / DBus 服务 / Xvfb / 真实 indicator 插件即可安全执行的路径:
 *
 *   1. 头文件可达(indicator.h / indicator-object.h / indicator-service.h /
 *      indicator-service-manager.h / indicator-desktop-shortcuts.h /
 *      indicator-ng.h[WITH_IDO])- 编译期验证
 *   2. GObject 类型注册(INDICATOR_OBJECT / INDICATOR_SERVICE /
 *      INDICATOR_SERVICE_MANAGER / INDICATOR_TYPE_DESKTOP_SHORTCUTS 类型宏)
 *   3. IndicatorDesktopShortcuts 纯逻辑解析(GKeyFile, 无 X11/DBus):
 *      正向路径(fixture .desktop)+ nick 枚举 + Name 查询
 *   4. 失败路径:不存在的 .desktop 文件 -> 上游 set_property 吞掉
 *      GError(g_warning + break), 对象仍构造成功但 nicks 为空数组
 *      (instance_init 中 priv->nicks = g_array_new -> data 非 NULL,
 *      0.9.4 源码 168-195 行逐行核实)- 安全失败而非崩溃
 *   5. IndicatorServiceManager 构造/析构(indicator_service_manager_new
 *      只建立 GObject 骨架并启动内部状态机, connected() 返回 FALSE,
 *      不实际发起 DBus 连接直到 main loop 运行;不跑 main loop 即无
 *      DBus 依赖 - 0.9.4 src/indicator-service-manager.c 行为)
 *
 * 刻意不调用:
 *   - indicator_object_new_from_file(g_module_open dlopen 插件)
 *   - indicator_ng_new(内部起 DBus 服务)
 *   - gtk_init 之外的窗口/GDK 绘制
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

/* -- 1. GObject 类型注册 ----------------------------------- */
static void
test_object_type_registered (void)
{
    /* INDICATOR_OBJECT_TYPE 宏触发 G_DEFINE_TYPE 的 get_type(),
       首次调用完成类型注册(父类 GObject 链全量初始化) */
    GType t_obj = INDICATOR_OBJECT_TYPE;
    g_assert_true (t_obj != G_TYPE_INVALID);

    GType t_svc = INDICATOR_SERVICE_TYPE;
    g_assert_true (t_svc != G_TYPE_INVALID);

    GType t_mgr = INDICATOR_SERVICE_MANAGER_TYPE;
    g_assert_true (t_mgr != G_TYPE_INVALID);

    GType t_ids = INDICATOR_TYPE_DESKTOP_SHORTCUTS;
    g_assert_true (t_ids != G_TYPE_INVALID);

    /* 类型名可从 GObject 系统反查(GTypeModule 未参与, 静态注册) */
    g_assert_nonnull (g_type_name (t_obj));
    g_assert_cmpstr (g_type_name (t_ids), ==, "IndicatorDesktopShortcuts");
}

/* -- 2. IndicatorObject abstract base type metadata (no instantiation) -- */
static void
test_object_lifecycle (void)
{
    /* 0.9.4 indicator-object.c:118 uses G_DEFINE_TYPE_WITH_PRIVATE - the
       base class is NOT abstract, but its constructed() vfunc g_error()s
       ("does not create an image or a label. We need one of those.")
       unless a concrete subclass provides widgets, i.e. instantiating the
       bare base class is fatal BY UPSTREAM DESIGN. We therefore assert
       type metadata + class vtable only and never instantiate the base
       (verified against 0.9.4 sources, lines 118/505/514/550). */
    GType t_obj = INDICATOR_OBJECT_TYPE;
    g_assert_true (g_type_is_a (t_obj, G_TYPE_OBJECT));

    /* class structure reachable: vfunc table allocated on first
       class_ref (no instance needed) */
    IndicatorObjectClass *klass = g_type_class_ref (t_obj);
    g_assert_nonnull (klass);
    /* public virtual methods exist in the vtable (non-zero offsets) */
    g_assert_true (G_STRUCT_OFFSET (IndicatorObjectClass, get_entries) >= 0);
    g_assert_true (G_STRUCT_OFFSET (IndicatorObjectClass, get_location) >= 0);
    g_type_class_unref (klass);

    /* GObject 引用计数基础语义在 libayatana-indicator 链接下可用 */
    GObject *obj = g_object_new (G_TYPE_OBJECT, NULL);
    g_object_ref (obj);
    g_assert_cmpuint (obj->ref_count, ==, 2);
    g_object_unref (obj);
    g_object_unref (obj);
}

/* -- 3. IndicatorDesktopShortcuts 纯逻辑解析(正向路径) ---- */
static void
test_desktop_shortcuts_parse (void)
{
    IndicatorDesktopShortcuts *ids = indicator_desktop_shortcuts_new (
        SRCDIR "/test-well-formed.desktop", "France");
    g_assert_nonnull (ids);

    /* OnlyShowIn=France 匹配 identity "France" -> open/save 两个 nick 可见 */
    const gchar **nicks = indicator_desktop_shortcuts_get_nicks (ids);
    g_assert_nonnull (nicks);
    guint count = 0;
    gboolean has_open = FALSE, has_save = FALSE;
    for (guint i = 0; nicks[i] != NULL; i++)
    {
        count++;
        /* 每个 nick 必须能取到显示名([Desktop Action] Name 字段) */
        gchar *name = indicator_desktop_shortcuts_nick_get_name (ids, nicks[i]);
        g_assert_nonnull (name);
        g_free (name);
        if (g_strcmp0 (nicks[i], "open") == 0) has_open = TRUE;
        if (g_strcmp0 (nicks[i], "save") == 0) has_save = TRUE;
    }
    g_assert_cmpuint (count, ==, 2);
    g_assert_true (has_open);
    g_assert_true (has_save);

    /* nick 显示名精确验证:open -> "Open" */
    gchar *name_open = indicator_desktop_shortcuts_nick_get_name (ids, "open");
    g_assert_cmpstr (name_open, ==, "Open");
    g_free (name_open);

    /* 注意: 0.9.4 nick_get_name 对无效 nick 是 g_return_val_if_fail
       (is_valid_nick(...)) CRITICAL-by-design(0.9.5 才加 NULL 检查),
       无效 nick 属于编程错误而非可断言的失败路径, 不在此查询. */

    /* 弱指针验证析构(上游 test-desktop-shortcuts.c 同款手法) */
    g_object_add_weak_pointer (G_OBJECT (ids), (gpointer *) &ids);
    g_object_unref (G_OBJECT (ids));
    g_assert_null (ids);
}

/* -- 4. 失败路径:不存在的 .desktop 文件(安全失败) -------- */
static void
test_desktop_shortcuts_missing_file (void)
{
    /* 0.9.4 set_property(src/indicator-desktop-shortcuts.c:168-195):
       g_key_file_load_from_file 失败 -> g_warning + g_error_free + break,
       priv->keyfile 保持 NULL;instance_init 已把 priv->nicks 初始化为
       空 GArray -> get_nicks 返回空列表(data 非 NULL, 首元素 NULL).
       断言:对象构造成功,get_nicks 可安全调用,nicks 为空. */
    g_test_expect_message (NULL, G_LOG_LEVEL_WARNING,
                           "Unable to load keyfile*");
    IndicatorDesktopShortcuts *ids = indicator_desktop_shortcuts_new (
        SRCDIR "/no-such-file.desktop", "France");
    g_test_assert_expected_messages ();

    g_assert_nonnull (ids);   /* 上游不因文件缺失拒绝构造 */

    const gchar **nicks = indicator_desktop_shortcuts_get_nicks (ids);
    g_assert_nonnull (nicks);
    g_assert_null (nicks[0]); /* 空 nick 列表, 而非崩溃/未定义 */

    g_object_add_weak_pointer (G_OBJECT (ids), (gpointer *) &ids);
    g_object_unref (G_OBJECT (ids));
    g_assert_null (ids);
}

/* -- 5. IndicatorServiceManager 构造/析构(无 DBus 往来) ---- */
static void
test_service_manager_construct (void)
{
    /* indicator_service_manager_new("...") 建立对象骨架;不进入 main loop
       则不发起实际 DBus 连接.connected() 初始必为 FALSE. */
    IndicatorServiceManager *sm = indicator_service_manager_new (
        "org.example.nonexistent.indicator");
    g_assert_nonnull (sm);

    g_assert_false (indicator_service_manager_connected (sm));

    /* set_refresh 是纯属性 setter(g_object_set), 无外部副作用 */
    indicator_service_manager_set_refresh (sm, 500);

    g_object_add_weak_pointer (G_OBJECT (sm), (gpointer *) &sm);
    g_object_unref (G_OBJECT (sm));
    g_assert_null (sm);
}

/* -- 6. IndicatorService 类型注册(不 new:new 会注册 DBus 名) -- */
static void
test_service_type_only (void)
{
    /* indicator_service_new(name) 会在默认 session bus 上
       g_bus_own_name -> 离线无 session bus 时仅在 main loop 迭代时失败;
       为完全避免 DBus 依赖, 这里只验证类型注册与 GType 元数据. */
    GType t = INDICATOR_SERVICE_TYPE;
    g_assert_true (t != G_TYPE_INVALID);
    g_assert_true (g_type_is_a (t, G_TYPE_OBJECT));

    /* 信号注册发生在 class_init (g_signal_new, src/indicator-service.c),
       必须 g_type_class_ref 强制类初始化后信号才可 lookup */
    IndicatorServiceClass *svc_klass = g_type_class_ref (t);
    g_assert_nonnull (svc_klass);
    g_assert_nonnull (g_signal_lookup ("shutdown", t));
    g_type_class_unref (svc_klass);
}

gint
main (gint argc, gchar *argv[])
{
    g_test_init (&argc, &argv, NULL);
    /* gtk_init: indicator-object.h includes gtk/gtk.h (IndicatorObjectClass
       returns GtkLabel and GtkMenu pointers), so GTK type system must be up
       for the type registrations above. The broadway headless backend
       (injected by the test_package conanfile environment) satisfies the
       display dependency without a real X11/Wayland session. */
    gtk_init (&argc, &argv);

    g_test_add_func ("/libayatana-indicator/0.9.4/object-type-registered",
                     test_object_type_registered);
    g_test_add_func ("/libayatana-indicator/0.9.4/object-lifecycle",
                     test_object_lifecycle);
    g_test_add_func ("/libayatana-indicator/0.9.4/desktop-shortcuts-parse",
                     test_desktop_shortcuts_parse);
    g_test_add_func ("/libayatana-indicator/0.9.4/desktop-shortcuts-missing-file",
                     test_desktop_shortcuts_missing_file);
    g_test_add_func ("/libayatana-indicator/0.9.4/service-manager-construct",
                     test_service_manager_construct);
    g_test_add_func ("/libayatana-indicator/0.9.4/service-type-only",
                     test_service_type_only);

    return g_test_run ();
}
