#include <glib.h>
#include <libayatana-indicator/indicator-object.h>
#include <libayatana-indicator/indicator.h>

int main(void) {
    GType t = indicator_object_get_type();
    if (t == G_TYPE_INVALID) {
        g_printerr("indicator_object_get_type() 返回 G_TYPE_INVALID\n");
        return 1;
    }
    g_print("indicator_object type registered: %s\n", g_type_name(t));

    /* 无 DBus 会话时 indicator_object_new_from_file 会返回 NULL（初始化失败），
       属预期行为；此处验证类型系统与符号链接即可。 */
    if (!g_type_is_a(t, G_TYPE_OBJECT)) {
        g_printerr("indicator_object type 不是 GObject 子类\n");
        return 2;
    }
    g_print("indicator_object is a GObject subtype: OK\n");
    g_print("test libayatana 0.9.5: OK\n");
    return 0;
}
