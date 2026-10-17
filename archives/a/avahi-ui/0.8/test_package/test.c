#include <stdio.h>
#include <string.h>

#include <glib-object.h>
#include <gtk/gtk.h>

/* Real consumer of the avahi-ui public API: GObject type-reflection checks on
 * AuiServiceDialog.  Headless CI sandboxes have no display server, so the
 * tests avoid instantiating a real GtkDialog and only exercise the type
 * machinery the library publishes. */
#include <avahi-ui/avahi-ui.h>

static int checks;
static int passed;

static void check(int condition, const char *message) {
    checks++;
    if (condition) {
        passed++;
    } else {
        fprintf(stderr, "FAIL: %s\n", message);
    }
}

int main(void) {
    GType dialog_type = aui_service_dialog_get_type();
    GTypeClass *klass = NULL;
    GParamSpec *spec = NULL;

    check(dialog_type != G_TYPE_INVALID,
          "aui_service_dialog_get_type() returns a registered GType");
    check(strcmp(g_type_name(dialog_type), "AuiServiceDialog") == 0,
          "registered type is named AuiServiceDialog");
    check(g_type_is_a(dialog_type, GTK_TYPE_DIALOG),
          "AuiServiceDialog derives from GtkDialog");
    check(g_type_is_a(dialog_type, G_TYPE_OBJECT),
          "AuiServiceDialog is a GObject-derived type");

    klass = g_type_class_ref(dialog_type);
    check(klass != NULL, "AuiServiceDialog class can be referenced");

    if (klass != NULL) {
        /* Properties installed by aui_service_dialog_class_init(). */
        spec = g_object_class_find_property(
            (GObjectClass *) klass, "browse_service_types");
        check(spec != NULL,
              "AuiServiceDialog publishes browse-service-types property");
        spec = g_object_class_find_property(
            (GObjectClass *) klass, "domain");
        check(spec != NULL, "AuiServiceDialog publishes domain property");
        g_type_class_unref(klass);
    }

    printf(
        "HMBS_TEST_PACKAGE_RESULT="
        "{\"executed\":true,\"passed\":%s,"
        "\"command\":\"test_avahi_ui\","
        "\"discovered\":%d,\"passedCount\":%d}\n",
        checks == passed ? "true" : "false", checks, passed);

    return checks == passed && checks == 7 ? 0 : 1;
}