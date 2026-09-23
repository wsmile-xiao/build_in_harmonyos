/*
 * test_package consumer test — really calls ayatana-ido public API (R34).
 * Covers: ido_init / ido_calendar_menu_item_new / IDO_IS_CALENDAR_MENU_ITEM /
 *         ido_entry_menu_item_new / IDO_IS_ENTRY_MENU_ITEM
 * Two checks; each prints a "menu item OK" line on success and the harness
 * counts them for the HMBS_TEST_PACKAGE_RESULT machine-evidence marker.
 */
#include <gtk/gtk.h>
#include <libayatana-ido/libayatana-ido.h>

int main(void) {
    int rc = 0;
    gint argc = 0;
    gchar **argv = NULL;

    gtk_init(&argc, &argv);
    ido_init();

    {
        GtkWidget *cal = ido_calendar_menu_item_new();
        if (!cal || !IDO_IS_CALENDAR_MENU_ITEM(cal) || !GTK_IS_MENU_ITEM(cal)) {
            g_printerr("test_ayatana-ido: calendar menu item invalid\n");
            rc = 1;
        } else {
            g_print("test_ayatana-ido: calendar menu item OK\n");
        }
        if (cal) g_object_ref_sink(cal), g_object_unref(cal);
    }

    {
        GtkWidget *entry = ido_entry_menu_item_new();
        if (!entry || !IDO_IS_ENTRY_MENU_ITEM(entry)) {
            g_printerr("test_ayatana-ido: entry menu item invalid\n");
            rc = 1;
        } else {
            g_print("test_ayatana-ido: entry menu item OK\n");
        }
        if (entry) g_object_ref_sink(entry), g_object_unref(entry);
    }

    g_print("test_ayatana-ido: %s\n", rc == 0 ? "PASS" : "FAIL");
    return rc;
}
