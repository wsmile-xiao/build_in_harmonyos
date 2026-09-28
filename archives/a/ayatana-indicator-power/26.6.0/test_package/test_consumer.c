/* test_consumer.c — HarmonyOS 端到端消费者用例 for ayatana-indicator-power
 *
 * OHOS PC 无 dbus-daemon/会话总线，因此这里用 GDBusServer 私有 peer 连接
 * 驱动包内真实服务二进制（ayu 服务以 AIP_TEST_BUS_ADDR 指向该 peer socket，
 * 在 peer 连接上导出其全部真实 D-Bus 对象）：
 *
 *   1. 启动 GDBusServer (unix:tmpdir)
 *   2. 以 AIP_TEST_BUS_ADDR=<socket> 环境变量拉起包内服务二进制
 *   3. 等服务 Testing 对象可用（org.ayatana.indicator.power.Testing）
 *   4. 走真实功能流程：开启 mock 电池 -> 设置电量 80% ->
 *      读取 org.ayatana.indicator.power.Battery 属性并断言真实计算值
 *      (PowerPercentage=80 / IsDischarging=true / PowerLevel="ok")
 *
 * 整个流程跨进程、走真实 GDBus 协议与 skeleton 实现，非纯断言。
 *
 * 用法: test_consumer <path-to-ayatana-indicator-power-service>
 * 退出码: 0 = 全部断言通过; 1 = 失败
 */
#include <gio/gio.h>
#include <glib.h>
#include <glib-unix.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define BUS_PATH        "/org/ayatana/indicator/power"
#define TESTING_PATH    BUS_PATH "/Testing"
#define BATTERY_PATH    BUS_PATH "/Battery"
#define TESTING_IFACE   "org.ayatana.indicator.power.Testing"
#define BATTERY_IFACE   "org.ayatana.indicator.power.Battery"
#define PROPS_IFACE     "org.freedesktop.DBus.Properties"
#define READY_TIMEOUT_MS 20000

static GDBusConnection *srv_conn = NULL;   /* 与服务的 peer 连接 */
static GPid child_pid = 0;
static int failures = 0;

static void
on_new_connection (GDBusServer     *server G_GNUC_UNUSED,
                   GDBusConnection *conn,
                   gpointer         data G_GNUC_UNUSED)
{
  /* 服务进程连上了我们的 GDBusServer —— 保留连接，稍后以 peer 方式调用 */
  if (srv_conn == NULL)
    srv_conn = g_object_ref (conn);
}

static void
check (const gchar * what, gboolean ok, const gchar * detail)
{
  if (ok)
    g_print ("[test] ✅ %s%s%s\n", what, detail ? " = " : "", detail ? detail : "");
  else
    {
      failures++;
      g_printerr ("[test] ❌ %s%s%s\n", what, detail ? " = " : "", detail ? detail : "");
    }
}

/* 同步调用服务导出对象的一个属性 Get，返回解析后的 GVariant（调用者 unref） */
static GVariant *
props_get (const gchar * path, const gchar * iface, const gchar * prop,
           GError ** err_out)
{
  g_autoptr(GVariant) reply = NULL;
  GError * error = NULL;

  reply = g_dbus_connection_call_sync (srv_conn,
                                       NULL,               /* peer 目标 */
                                       path,
                                       PROPS_IFACE,
                                       "Get",
                                       g_variant_new ("(ss)", iface, prop),
                                       G_VARIANT_TYPE ("(v)"),
                                       G_DBUS_CALL_FLAGS_NONE,
                                       3000, NULL, &error);
  if (reply == NULL)
    {
      if (err_out != NULL)
        *err_out = error;
      else
        g_clear_error (&error);
      return NULL;
    }

  {
    GVariant * value = NULL;
    g_variant_get (reply, "(v)", &value);
    return value;   /* 转移给调用者 */
  }
}

static gboolean
props_set (const gchar * path, const gchar * iface, const gchar * prop,
           GVariant * value, GError ** err_out)
{
  g_autoptr(GVariant) reply = NULL;
  GError * error = NULL;

  reply = g_dbus_connection_call_sync (srv_conn,
                                       NULL,
                                       path,
                                       PROPS_IFACE,
                                       "Set",
                                       g_variant_new ("(ssv)", iface, prop, value),
                                       NULL,
                                       G_DBUS_CALL_FLAGS_NONE,
                                       3000, NULL, &error);
  if (reply == NULL)
    {
      if (err_out != NULL)
        *err_out = error;
      return FALSE;
    }
  return TRUE;
}

int
main (int argc, char ** argv)
{
  g_autoptr(GDBusServer) server = NULL;
  g_autofree gchar * addr = NULL;
  g_autoptr(GError) error = NULL;
  g_autoptr(GMainContext) ctx = NULL;
  g_autoptr(GVariant) v = NULL;
  guint64 deadline;
  gulong sig_id;

  if (argc < 2)
    {
      g_printerr ("[test] 用法: %s <ayatana-indicator-power-service>\n", argv[0]);
      return 2;
    }

  /* 1. 私有 peer server（glib 2.88 要求合法 GUID，不能为 NULL）
   * 注意: OHOS 沙箱禁止文件系统型 UNIX socket（bind 得 EPERM/EACCES），
   * 而 abstract namespace socket 可用 → 用 unix:abstract= 地址（不落盘）。 */
  g_autofree gchar * guid = g_dbus_generate_guid ();
  g_autofree gchar * server_addr = g_strdup_printf ("unix:abstract=aip-consumer-%ld-%d",
                                                    (long)g_get_real_time (), getpid ());
  server = g_dbus_server_new_sync (server_addr,
                                   G_DBUS_SERVER_FLAGS_AUTHENTICATION_ALLOW_ANONYMOUS,
                                   guid, NULL, NULL, &error);
  if (server == NULL)
    {
      g_printerr ("[test] ❌ GDBusServer 创建失败: %s\n",
                  error != NULL ? error->message : "(unknown)");
      return 1;
    }
  g_dbus_server_start (server);
  addr = g_strdup (g_dbus_server_get_client_address (server));
  g_print ("[test] GDBusServer 地址: %s\n", addr);

  /* 2. 拉起服务二进制 */
  {
    g_auto(GStrv) envp = NULL;
    gchar * child_argv[2];

    envp = g_get_environ ();
    envp = g_environ_setenv (envp, "AIP_TEST_BUS_ADDR", addr, TRUE);
    /* OHOS 无 dconf；GSettings 用 memory backend（schema 由 test 环境提供） */
    envp = g_environ_setenv (envp, "GSETTINGS_BACKEND", "memory", TRUE);
    envp = g_environ_setenv (envp, "G_MESSAGES_DEBUG", "all", TRUE);

    child_argv[0] = argv[1];
    child_argv[1] = NULL;
    if (!g_spawn_async (NULL, child_argv, envp,
                        G_SPAWN_DO_NOT_REAP_CHILD,
                        NULL, NULL, &child_pid, &error))
      {
        g_printerr ("[test] ❌ 无法拉起服务 %s: %s\n", argv[1], error->message);
        return 1;
      }
    g_print ("[test] 服务已拉起 pid=%d\n", (int)child_pid);
  }

  ctx = g_main_context_default ();
  sig_id = g_signal_connect (server, "new-connection",
                             G_CALLBACK (on_new_connection), NULL);

  /* 3. 等服务进程连上 peer server（最多 READY_TIMEOUT_MS） */
  deadline = g_get_monotonic_time () + READY_TIMEOUT_MS * 1000;
  while (srv_conn == NULL && g_get_monotonic_time () < deadline)
    {
      g_main_context_iteration (ctx, FALSE);
      g_usleep (50 * 1000);
    }
  if (srv_conn == NULL)
    {
      g_printerr ("[test] ❌ 服务未连上 peer server（超时）\n");
      goto out_fail;
    }
  g_print ("[test] 服务已连接 peer\n");

  /* 4. 等 Testing 对象可应答（服务完成导出后再驱动） */
  {
    gboolean ready = FALSE;
    while (!ready && g_get_monotonic_time () < deadline)
      {
        g_autoptr(GVariant) mv = props_get (TESTING_PATH, TESTING_IFACE,
                                            "MockBatteryLevel", NULL);
        if (mv != NULL)
          ready = TRUE;
        else
          g_usleep (50 * 1000);
      }
    if (!ready)
      {
        g_printerr ("[test] ❌ Testing 对象不可达（服务未就绪）\n");
        goto out_fail;
      }
    g_print ("[test] Testing 对象就绪\n");
  }

  /* 5. 端到端功能流程：mock 电池 -> 80% -> 断言 Battery 真实计算值 */
  g_print ("[test] 开启 mock 电池...\n");
  if (!props_set (TESTING_PATH, TESTING_IFACE, "MockBatteryEnabled",
                  g_variant_new_boolean (TRUE), &error))
    {
      g_printerr ("[test] ❌ 设置 MockBatteryEnabled 失败: %s\n", error->message);
      g_clear_error (&error);
      goto out_fail;
    }
  g_print ("[test] 设置 MockBatteryLevel=80 ...\n");
  if (!props_set (TESTING_PATH, TESTING_IFACE, "MockBatteryLevel",
                  g_variant_new_uint32 (80), &error))
    {
      g_printerr ("[test] ❌ 设置 MockBatteryLevel 失败: %s\n", error->message);
      g_clear_error (&error);
      goto out_fail;
    }

  /* 5a. Testing 对象属性回读（mock 状态真实生效） */
  v = props_get (TESTING_PATH, TESTING_IFACE, "MockBatteryLevel", &error);
  check ("Testing.MockBatteryLevel 回读", v != NULL, error ? error->message : NULL);
  if (v != NULL)
    {
      guint32 lvl = 0;
      g_variant_get (v, "u", &lvl);
      check ("MockBatteryLevel == 80", lvl == 80, g_strdup_printf ("%u", lvl));
      g_clear_pointer (&v, g_variant_unref);
    }
  g_clear_error (&error);

  /* 5b. Battery 对象真实属性（mock 设备驱动出的真实计算值） */
  v = props_get (BATTERY_PATH, BATTERY_IFACE, "PowerPercentage", &error);
  check ("Battery.PowerPercentage 可读", v != NULL, error ? error->message : NULL);
  if (v != NULL)
    {
      gint32 pct = -1;
      g_variant_get (v, "i", &pct);
      check ("PowerPercentage == 80", pct == 80, g_strdup_printf ("%d", pct));
      g_clear_pointer (&v, g_variant_unref);
    }
  g_clear_error (&error);

  v = props_get (BATTERY_PATH, BATTERY_IFACE, "IsDischarging", &error);
  check ("Battery.IsDischarging 可读", v != NULL, error ? error->message : NULL);
  if (v != NULL)
    {
      gboolean dis = FALSE;
      g_variant_get (v, "b", &dis);
      check ("IsDischarging == true", dis == TRUE, dis ? "true" : "false");
      g_clear_pointer (&v, g_variant_unref);
    }
  g_clear_error (&error);

  v = props_get (BATTERY_PATH, BATTERY_IFACE, "PowerLevel", &error);
  check ("Battery.PowerLevel 可读", v != NULL, error ? error->message : NULL);
  if (v != NULL)
    {
      const gchar * lvl = NULL;
      g_variant_get (v, "&s", &lvl);
      check ("PowerLevel == ok", lvl != NULL && g_strcmp0 (lvl, "ok") == 0,
             lvl ? lvl : "(null)");
      g_clear_pointer (&v, g_variant_unref);
    }
  g_clear_error (&error);

  g_signal_handler_disconnect (server, sig_id);
  if (child_pid > 0)
    {
      g_spawn_close_pid (child_pid);
      kill (child_pid, SIGTERM);
    }
  g_clear_object (&srv_conn);

  if (failures > 0)
    {
      g_printerr ("[test] ❌ 消费者用例失败: %d 处断言未通过\n", failures);
      return 1;
    }
  g_print ("[test] ✅ 端到端消费者用例通过：服务真实运行，mock 电池 80%% 经真实 "
           "D-Bus 流程驱动出 PowerPercentage=80/IsDischarging=true/PowerLevel=ok\n");
  return 0;

out_fail:
  if (child_pid > 0)
    kill (child_pid, SIGTERM);
  g_clear_object (&srv_conn);
  return 1;
}
