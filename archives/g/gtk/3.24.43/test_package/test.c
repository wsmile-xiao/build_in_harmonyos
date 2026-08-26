#include <gtk/gtk.h>
#include <stdio.h>

int main(int argc, char *argv[]) {
    // R34: must call tested package API, not just print string
    // Verify GTK version API (no display needed)
    unsigned int major = gtk_get_major_version();
    unsigned int minor = gtk_get_minor_version();
    unsigned int micro = gtk_get_micro_version();
    printf("GTK %u.%u.%u\n", major, minor, micro);
    // Verify GDK API
    const char *ver = gtk_check_version(3, 24, 43);
    if (ver != NULL) {
        fprintf(stderr, "gtk_check_version failed: %s\n", ver);
        return 1;
    }
    // Verify GObject type system initialized via gtk
    GType t = gtk_widget_get_type();
    if (t == 0) {
        fprintf(stderr, "gtk_widget_get_type failed\n");
        return 1;
    }
    printf("gtk_widget type: %lu\n", (unsigned long)t);
    printf("test GTK 3.24.43: OK\n");
    return 0;
}
