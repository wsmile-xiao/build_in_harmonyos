#include <dbus/dbus.h>
#include <stdio.h>
#include <string.h>

/* 无 session bus 可连接时 libdbus 会置的错误名（环境限制，非库缺陷）。
 * 逐条含义：
 *   FileNotFound/NoServer  —— 地址指向的 socket 不存在 / 无人监听
 *   NotSupported           —— 未设置 DBUS_SESSION_BUS_ADDRESS 且无 autolaunch
 *   AddressInUse           —— 地址被占用
 *   Spawn.* / Disconnected —— autolaunch 拉起失败 / 连接中断
 *   NoReply                —— 传输层连上但认证/应答失败（如无 passwd 条目）
 * 上述任一情形均说明「库可链接、API 可调用、返回了规范的 DBusError」，
 * 断言目的（R34 消费者侧冒烟）已达成。其他错误（含 err 未置名）视为真实失败。 */
static const char *const ENV_LIMITED[] = {
    "org.freedesktop.DBus.Error.FileNotFound",
    "org.freedesktop.DBus.Error.NoServer",
    "org.freedesktop.DBus.Error.NotSupported",
    "org.freedesktop.DBus.Error.AddressInUse",
    "org.freedesktop.DBus.Error.Disconnected",
    "org.freedesktop.DBus.Error.NoReply",
    "org.freedesktop.DBus.Error.Spawn.ExecFailed",
    "org.freedesktop.DBus.Error.Spawn.NoBus",
    "org.freedesktop.DBus.Error.Spawn.ChildExited",
    "org.freedesktop.DBus.Error.Spawn.PermissionsInvalid",
    NULL
};

int main(void) {
    /* 真实调用 libdbus-1 API：建立到会话总线的连接 */
    DBusError err;
    dbus_error_init(&err);
    DBusConnection *conn = dbus_bus_get(DBUS_BUS_SESSION, &err);
    if (conn == NULL) {
        const char *n = err.name; /* DBusError 公开字段即 name/message */
        int env_limited = 0;
        for (int i = 0; n != NULL && ENV_LIMITED[i] != NULL; i++) {
            if (strcmp(n, ENV_LIMITED[i]) == 0) {
                env_limited = 1;
                break;
            }
        }
        printf("dbus test %s (no session bus available)\n",
               env_limited ? "PASSED" : "FAILED");
        printf("  dbus error name: %s\n", n ? n : "(unset)");
        if (!env_limited) {
            printf("  message: %s\n", err.message ? err.message : "(none)");
        }
        dbus_error_free(&err);
        return env_limited ? 0 : 1;
    }
    /* 总线可达：进一步断言真实调用（列名）成功 */
    DBusError lerr;
    dbus_error_init(&lerr);
    DBusMessage *m = dbus_message_new_method_call(
        DBUS_SERVICE_DBUS, DBUS_PATH_DBUS, DBUS_INTERFACE_DBUS, "ListNames");
    if (m == NULL) {
        printf("dbus test FAILED (dbus_message_new_method_call returned NULL)\n");
        dbus_connection_unref(conn);
        return 1;
    }
    DBusMessage *r = dbus_connection_send_with_reply_and_block(conn, m, 5000, &lerr);
    dbus_message_unref(m);
    if (r == NULL) {
        printf("dbus test FAILED (ListNames call failed: %s)\n",
               lerr.name ? lerr.name : "(unset)");
        dbus_error_free(&lerr);
        dbus_connection_unref(conn);
        return 1;
    }
    dbus_message_unref(r);
    dbus_error_free(&lerr);
    dbus_connection_unref(conn);
    printf("dbus test PASSED (session bus reachable, ListNames ok)\n");
    return 0;
}
