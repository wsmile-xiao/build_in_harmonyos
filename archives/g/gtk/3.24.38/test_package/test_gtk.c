#include <gtk/gtk.h>
#include <stdio.h>

int main(void) {
    if (gtk_get_major_version() != 3) {
        return 1;
    }
    if (gtk_get_minor_version() < 24) {
        return 2;
    }
    if (gtk_check_version(3, 24, 0) != NULL) {
        return 3;
    }
    GType window_type = gtk_window_get_type();
    if (window_type == G_TYPE_INVALID || g_type_name(window_type) == NULL) {
        return 4;
    }
    printf(
        "PASS gtk+ %u.%u.%u type=%s\n",
        gtk_get_major_version(), gtk_get_minor_version(), gtk_get_micro_version(),
        g_type_name(window_type)
    );
    return 0;
}
