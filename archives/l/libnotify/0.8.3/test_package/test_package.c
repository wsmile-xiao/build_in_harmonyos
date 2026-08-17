#include <libnotify/notify.h>
#include <stdlib.h>

int main(void) {
    /* libnotify 依赖 DBus 会话总线，鸿蒙环境无 dbus 运行时，仅验证编译与链接 */
    gboolean ok = notify_init("test");
    if (ok) {
        notify_uninit();
    }
    return 0;
}
