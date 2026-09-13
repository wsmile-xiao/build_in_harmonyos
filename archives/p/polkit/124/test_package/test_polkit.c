#include <polkit/polkit.h>
#include <glib.h>
#include <stdio.h>

/* Validates that libpolkit-gobject-1 installs usable headers and that its
 * pure GObject API (no running polkitd / system bus needed) works. */
int main(void) {
    PolkitIdentity *identity = polkit_unix_user_new(0);
    if (identity == NULL) {
        g_printerr("polkit_unix_user_new() returned NULL\n");
        return 1;
    }
    if (!G_IS_OBJECT(identity)) {
        g_printerr("PolkitIdentity is not a GObject (library not loaded?)\n");
        g_object_unref(identity);
        return 1;
    }
    gchar *identity_str = polkit_identity_to_string(identity);
    if (identity_str == NULL || identity_str[0] == '\0') {
        g_printerr("polkit_identity_to_string() returned empty\n");
        g_object_unref(identity);
        return 1;
    }

    PolkitSubject *subject = polkit_system_bus_name_new(":1.42");
    if (subject == NULL) {
        g_printerr("polkit_system_bus_name_new() returned NULL\n");
        g_object_unref(identity);
        return 1;
    }
    gchar *subject_str = polkit_subject_to_string(subject);
    if (subject_str == NULL || subject_str[0] == '\0') {
        g_printerr("polkit_subject_to_string() returned empty\n");
        g_object_unref(identity);
        g_object_unref(subject);
        return 1;
    }

    g_print("polkit-gobject-1 OK: identity=%s subject=%s\n", identity_str, subject_str);
    g_free(identity_str);
    g_free(subject_str);
    g_object_unref(identity);
    g_object_unref(subject);
    return 0;
}
