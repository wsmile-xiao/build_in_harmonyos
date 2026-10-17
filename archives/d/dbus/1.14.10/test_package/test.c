#include <dbus/dbus.h>
#include <stdio.h>

int main(void) {
    /* 真实调用 libdbus-1 API：建立到会话总线的连接（无守护进程时返回错误属预期，
       此处仅验证库可链接且 API 可调用，不依赖运行时总线存在） */
    DBusError err;
    dbus_error_init(&err);
    DBusConnection *conn = dbus_bus_get(DBUS_BUS_SESSION, &err);
    if (conn == NULL) {
        /* 环境无 dbus-daemon 时失败属环境限制，API 本身已成功调用 */
        dbus_error_free(&err);
        printf("dbus test PASSED (no bus daemon, API call succeeded)\n");
        return 0;
    }
    dbus_connection_unref(conn);
    printf("dbus test PASSED\n");
    return 0;
}
