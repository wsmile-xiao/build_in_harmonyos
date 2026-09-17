#include <dbus/dbus.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* 消费方验证：连接会话总线完成一次 D-Bus 往返（org.freedesktop.DBus Peer.Ping）。
 * 若环境提供了 DBUS_SESSION_BUS_ADDRESS（dbus-daemon 会话总线地址），必须完成
 * 真实调用并得到回复，否则退出码非 0；无地址时如实说明并退出 0（不伪造通过）。 */
static int do_roundtrip(const char *address) {
    DBusError err;
    DBusConnection *conn;
    DBusMessage *msg = NULL, *reply = NULL;
    int rc = 1;

    dbus_error_init(&err);
    conn = dbus_connection_open(address, &err);
    if (conn == NULL) {
        fprintf(stderr, "dbus_connection_open failed: %s: %s\n",
                err.name ? err.name : "?", err.message ? err.message : "?");
        dbus_error_free(&err);
        return 1;
    }
    /* 注册（发送 Hello） */
    if (!dbus_bus_register(conn, &err)) {
        fprintf(stderr, "dbus_bus_register failed: %s: %s\n",
                err.name ? err.name : "?", err.message ? err.message : "?");
        dbus_error_free(&err);
        dbus_connection_unref(conn);
        return 1;
    }
    msg = dbus_message_new_method_call("org.freedesktop.DBus", "/",
                                       "org.freedesktop.DBus.Peer", "Ping");
    if (msg == NULL) {
        fprintf(stderr, "OOM creating Ping\n");
        goto out;
    }
    reply = dbus_connection_send_with_reply_and_block(conn, msg, 5000, &err);
    if (reply == NULL) {
        fprintf(stderr, "Ping roundtrip failed: %s: %s\n",
                err.name ? err.name : "?", err.message ? err.message : "?");
        dbus_error_free(&err);
        goto out;
    }
    if (dbus_message_get_type(reply) == DBUS_MESSAGE_TYPE_METHOD_RETURN) {
        printf("dbus consumer roundtrip PASSED (method return)\n");
        rc = 0;
    } else {
        printf("dbus consumer roundtrip got unexpected reply type\n");
    }
    dbus_message_unref(reply);
    reply = NULL;
out:
    if (msg) dbus_message_unref(msg);
    dbus_connection_unref(conn);
    return rc;
}

int main(void) {
    const char *address = getenv("DBUS_SESSION_BUS_ADDRESS");
    DBusError err;
    DBusConnection *conn;

    if (address != NULL && *address != '\0') {
        printf("DBUS_SESSION_BUS_ADDRESS=%s\n", address);
        return do_roundtrip(address);
    }

    /* 无会话总线地址：验证 libdbus API 可链接调用；
     * 尝试会话总线属预期失败（无 daemon），如实报告，不伪造 PASS。 */
    dbus_error_init(&err);
    conn = dbus_bus_get(DBUS_BUS_SESSION, &err);
    if (conn == NULL) {
        fprintf(stderr, "NOTE: no session bus (DBUS_SESSION_BUS_ADDRESS unset), "
                "API linkage verified only: %s: %s\n",
                err.name ? err.name : "?", err.message ? err.message : "?");
        dbus_error_free(&err);
        return 0;
    }
    dbus_connection_unref(conn);
    printf("dbus session bus available but no address env; API verified\n");
    return 0;
}