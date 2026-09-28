/* test_portal_e2e.c — 鸿蒙特有完整消费者用例（端到端，E2E）。
 *
 * 与 L1 断言测试（test_libportal_gtk4.c）的区别：本用例跑通一条完整的
 * 消费者功能流程，而非孤立断言：
 *
 *   真实 session bus（conan dbus 包的 dbus-daemon，TCP 监听）
 *     → 同进程内以 GDBus 注册 mock org.freedesktop.portal.Desktop 后端
 *       （Settings.ReadOne / ReadAll 方法，等价上游 pyportaltest 的 dbusmock 角色）
 *     → 经 libportal-gtk4 真实公开 API 发起 D-Bus 方法调用并消费返回值：
 *        xdp_portal_new()                       真实会话总线接入
 *        xdp_portal_get_settings()              Settings 对象构建
 *        xdp_settings_read_string()             ReadOne 往返（序列化/反序列化）
 *        xdp_settings_read_all_values()         ReadAll 往返（嵌套 a{sa{sv}}）
 *        未知 key                               错误路径（GError 传播）
 *        xdp_parent_new_gtk()                   GTK4 backend 交付物真实消费
 *
 * 上游 pyportaltest（81 例）依赖 python-dbus/dbusmock/PyGObject/GI 绑定，
 * OHOS CI 与真机均不可得（见 PR 正文与上游测试报告）；本用例用 C/GDBus
 * 实现等价 mock portal 后端，使端到端功能流在 OHOS 上可确定性复现。
 */
#include <gio/gio.h>
#include <gtk/gtk.h>
#include <libportal/portal.h>
#include <libportal/portal-helpers.h>
#include <libportal-gtk4/portal-gtk4.h>

#include <stdio.h>
#include <string.h>

#define PORTAL_BUS_NAME "org.freedesktop.portal.Desktop"
#define PORTAL_OBJECT_PATH "/org/freedesktop/portal/desktop"
#define SETTINGS_IFACE "org.freedesktop.portal.Settings"

#define MOCK_NS "oh.e2e"
#define MOCK_KEY "probe"
#define MOCK_VALUE "oh-pc-e2e-ok"
#define MOCK_ALL_VALUE "oh-pc-e2e-all"

static GMainLoop *loop = NULL;
static int test_rc = 1;
static int g_registered = 0;

static const gchar *mock_portal_xml =
    "<node>"
    "  <interface name='org.freedesktop.portal.Settings'>"
    "    <method name='ReadOne'>"
    "      <arg type='s' direction='in' name='namespace'/>"
    "      <arg type='s' direction='in' name='key'/>"
    "      <arg type='v' direction='out' name='value'/>"
    "    </method>"
    "    <method name='ReadAll'>"
    "      <arg type='as' direction='in' name='namespaces'/>"
    "      <arg type='a{sa{sv}}' direction='out' name='value'/>"
    "    </method>"
    "    <signal name='SettingChanged'>"
    "      <arg type='s' name='namespace'/>"
    "      <arg type='s' name='key'/>"
    "      <arg type='v' name='value'/>"
    "    </signal>"
    "  </interface>"
    "</node>";

/* ---- mock portal 后端：Settings 接口方法分发 ---- */

static void
handle_method_call (GDBusConnection       *connection,
                    const gchar           *sender,
                    const gchar           *object_path,
                    const gchar           *interface_name,
                    const gchar           *method_name,
                    GVariant              *parameters,
                    GDBusMethodInvocation *invocation,
                    gpointer               user_data)
{
  if (g_strcmp0 (method_name, "ReadOne") == 0)
    {
      const char *ns = NULL;
      const char *key = NULL;
      g_variant_get (parameters, "(&s&s)", &ns, &key);
      if (g_strcmp0 (ns, MOCK_NS) == 0 && g_strcmp0 (key, MOCK_KEY) == 0)
        {
          GVariant *val = g_variant_new_string (MOCK_VALUE);
          g_dbus_method_invocation_return_value (invocation,
                                                 g_variant_new ("(v)", val));
          return;
        }
      /* 未知 key：返回 D-Bus 错误，供消费者验证错误传播路径 */
      g_dbus_method_invocation_return_error (invocation,
                                             G_DBUS_ERROR,
                                             G_DBUS_ERROR_INVALID_ARGS,
                                             "mock portal: no such setting %s.%s",
                                             ns, key);
      return;
    }

  if (g_strcmp0 (method_name, "ReadAll") == 0)
    {
      /* 返回 a{sa{sv}}：{ "oh.e2e" → { "probe" → "oh-pc-e2e-all" } } */
      GVariantBuilder dict;
      g_variant_builder_init (&dict, G_VARIANT_TYPE ("a{sa{sv}}"));
      g_variant_builder_open (&dict, G_VARIANT_TYPE ("{sa{sv}}"));
      g_variant_builder_add (&dict, "s", MOCK_NS);
      g_variant_builder_open (&dict, G_VARIANT_TYPE ("a{sv}"));
      g_variant_builder_add (&dict, "{sv}", MOCK_KEY,
                             g_variant_new_string (MOCK_ALL_VALUE));
      g_variant_builder_close (&dict);
      g_variant_builder_close (&dict);
      g_dbus_method_invocation_return_value (
          invocation, g_variant_new ("(@a{sa{sv}})", g_variant_builder_end (&dict)));
      return;
    }

  g_dbus_method_invocation_return_error (invocation, G_DBUS_ERROR,
                                         G_DBUS_ERROR_UNKNOWN_METHOD,
                                         "mock portal: unknown method %s",
                                         method_name);
}

static const GDBusInterfaceVTable mock_vtable = {
    handle_method_call, NULL, NULL, {0},
};

static void
on_bus_acquired (GDBusConnection *connection, const gchar *name, gpointer user_data)
{
  GDBusNodeInfo *info = g_dbus_node_info_new_for_xml (mock_portal_xml, NULL);
  if (info == NULL || info->interfaces[0] == NULL)
    {
      g_printerr ("E2E FAIL: cannot parse mock portal introspection XML\n");
      test_rc = 2;
      g_main_loop_quit (loop);
      return;
    }
  GError *err = NULL;
  guint reg = g_dbus_connection_register_object (
      connection, PORTAL_OBJECT_PATH, info->interfaces[0], &mock_vtable,
      NULL, NULL, &err);
  g_dbus_node_info_unref (info);
  if (reg == 0)
    {
      g_printerr ("E2E FAIL: register mock portal object failed: %s\n",
                  err ? err->message : "?");
      g_clear_error (&err);
      test_rc = 2;
      g_main_loop_quit (loop);
      return;
    }
  g_registered = 1;
}

static void
on_name_lost (GDBusConnection *connection, const gchar *name, gpointer user_data)
{
  g_printerr ("E2E FAIL: lost bus name %s (session bus unreachable?)\n", name);
  test_rc = 2;
  g_main_loop_quit (loop);
}

/* ---- 消费者流程：经 libportal-gtk4 公开 API 走完整功能链 ---- */

#define CHECK(step, cond, fmt, ...)                                            \
  do                                                                           \
    {                                                                          \
      if (cond)                                                                \
        printf ("  step %d PASS: " fmt "\n", step, __VA_ARGS__);               \
      else                                                                     \
        {                                                                      \
          printf ("  step %d FAIL: " fmt "\n", step, __VA_ARGS__);             \
          test_rc = 1;                                                         \
          g_main_loop_quit (loop);                                             \
          return NULL;                                                         \
        }                                                                      \
    }                                                                          \
  while (0)

/* 消费者流程运行在工作线程：GDBus 对注册对象的 method call 分发依赖
 * 主上下文，而同步调用（call_sync / libportal 同步 API）会阻塞调用者
 * 线程。若在主线程发起同步调用，主循环被堵住 → mock 无法分发 → 5s
 * 超时（本机实验实证）。工作线程发起调用 + 主循环保持分发，等价上游
 * pyportaltest 的跨连接 dbusmock 模型。 */
static gpointer
run_consumer_flow (gpointer data)
{
  int step = 0;
  GError *err = NULL;

  printf ("test_portal_e2e: mock portal backend ready, running consumer flow\n");

  /* Step 1: GTK4 backend 交付物真实消费（xdp_parent_new_gtk 符号解析 +
   * vtable 接线；headless 安全——不触碰窗口内部，CI 同款模式） */
  GObject *dummy = g_object_new (G_TYPE_OBJECT, NULL);
  XdpParent *parent = xdp_parent_new_gtk ((GtkWindow *) dummy);
  step++;
  CHECK (step, parent != NULL, "%s",
         "xdp_parent_new_gtk consumed libportal-gtk4.so");
  g_object_unref (dummy);

  /* Step 2: XdpPortal 真实接入 session bus（无 bus 时该 API 会 abort，
   * 因此能走到这里即证明真实总线接入成功） */
  XdpPortal *portal = xdp_portal_new ();
  step++;
  CHECK (step, portal != NULL, "%s",
         "xdp_portal_new() connected to session bus");

  /* Step 3: Settings 对象 */
  XdpSettings *settings = xdp_portal_get_settings (portal);
  step++;
  CHECK (step, settings != NULL, "%s",
         "xdp_portal_get_settings() built XdpSettings");

  /* Step 4: ReadOne 往返 —— 消费者请求经 session bus 到 mock 后端再返回 */
  char *val = xdp_settings_read_string (settings, MOCK_NS, MOCK_KEY, NULL, &err);
  step++;
  CHECK (step, val != NULL && strcmp (val, MOCK_VALUE) == 0,
         "Settings.ReadOne roundtrip -> \"%s\" (err=%s)",
         val ? val : "(null)", err ? err->message : "none");
  g_free (val);
  g_clear_error (&err);

  /* Step 5: ReadAll 往返（嵌套 a{sa{sv}} 反序列化） */
  const char *const namespaces[] = { MOCK_NS, NULL };
  GVariant *all = xdp_settings_read_all_values (settings, namespaces, NULL, &err);
  step++;
  if (all != NULL)
    {
      GVariant *ns_dict = g_variant_lookup_value (all, MOCK_NS,
                                                  G_VARIANT_TYPE ("a{sv}"));
      GVariant *v = ns_dict ? g_variant_lookup_value (ns_dict, MOCK_KEY,
                                                      G_VARIANT_TYPE_STRING)
                            : NULL;
      CHECK (step,
             v != NULL
                 && strcmp (g_variant_get_string (v, NULL), MOCK_ALL_VALUE) == 0,
         "Settings.ReadAll roundtrip -> ns=\"%s\" key=\"%s\" value=\"%s\"",
         MOCK_NS, MOCK_KEY,
         v ? g_variant_get_string (v, NULL) : "(missing)");
      if (v)
        g_variant_unref (v);
      if (ns_dict)
        g_variant_unref (ns_dict);
      g_variant_unref (all);
    }
  else
    {
      CHECK (step, 0, "Settings.ReadAll roundtrip -> null (err=%s)",
             err ? err->message : "none");
    }
  g_clear_error (&err);

  /* Step 6: 错误路径 —— 未知 key 返回 GError，消费者按 API 契约处理 */
  char *missing = xdp_settings_read_string (settings, MOCK_NS, "missing-key",
                                            NULL, &err);
  step++;
  CHECK (step, missing == NULL && err != NULL,
         "unknown key -> NULL + GError (%s)",
         err ? err->message : "no error!");
  g_free (missing);
  g_clear_error (&err);

  g_object_unref (settings);
  g_object_unref (portal);

  printf ("test_portal_e2e: all %d steps passed (end-to-end portal flow)\n",
          step);
  test_rc = 0;
  g_main_loop_quit (loop);
  return NULL;
}

static void
on_name_acquired (GDBusConnection *connection, const gchar *name, gpointer user_data)
{
  if (!g_registered)
    {
      g_printerr ("E2E FAIL: name acquired but mock object not registered\n");
      test_rc = 2;
      g_main_loop_quit (loop);
      return;
    }
  g_thread_new ("consumer-flow", run_consumer_flow, NULL);
}

int
main (int argc, char *argv[])
{
  loop = g_main_loop_new (NULL, FALSE);

  guint owner_id = g_bus_own_name (
      G_BUS_TYPE_SESSION, PORTAL_BUS_NAME, G_BUS_NAME_OWNER_FLAGS_NONE,
      on_bus_acquired, on_name_acquired, on_name_lost, NULL, NULL);

  g_main_loop_run (loop);
  g_bus_unown_name (owner_id);
  g_main_loop_unref (loop);

  if (test_rc == 0)
    printf ("test libportal-gtk4 0.10.0 E2E consumer flow: OK\n");
  return test_rc;
}
