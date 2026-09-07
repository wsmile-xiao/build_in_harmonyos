#include <stdio.h>
#include <stdlib.h>
#include <gvnc-1.0/gvnc.h>
#include <gtk-vnc-2.0/gtk-vnc.h>

int main(void) {
    VncConnection *conn;
    GType t;

    /* gvnc 连接 API（纯 GObject，无显示依赖） */
    conn = vnc_connection_new();
    if (conn == NULL) {
        fprintf(stderr, "vnc_connection_new returned NULL\n");
        return 1;
    }
    if (vnc_connection_get_type() == 0) {
        fprintf(stderr, "vnc_connection_get_type invalid\n");
        return 1;
    }
    if (!vnc_connection_set_shared(conn, FALSE)) {
        fprintf(stderr, "vnc_connection_set_shared failed\n");
        return 1;
    }
    g_object_unref(conn);

    /* gtk-vnc-2.0：仅验证类型系统注册（不实例化 GTK widget，
       避免无显示环境下 gtk_widget 崩溃；gtk 参考配方同款做法） */
    t = vnc_display_get_type();
    if (t == 0) {
        fprintf(stderr, "vnc_display_get_type invalid\n");
        return 1;
    }
    if (VNC_TYPE_DISPLAY != t) {
        fprintf(stderr, "VNC_TYPE_DISPLAY mismatch\n");
        return 1;
    }

    printf("gtk-vnc test: OK\n");
    return 0;
}
