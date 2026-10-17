/* Consumer test for libdbusmenu-gtk3 16.04.0.
 *
 * Exercises the public libdbusmenu-glib menu-model API as a real consumer:
 * builds a menu tree, sets/gets properties, appends children, looks items up
 * by id, and reads them back. These calls are plain GObject data-structure
 * operations and do not require a running D-Bus session bus.
 */
#include <libdbusmenu-glib/menuitem.h>
#include <libdbusmenu-glib/server.h>
#include <libdbusmenu-glib/client.h>
#include <string.h>

int main(void) {
    /* 1. root + children */
    DbusmenuMenuitem *root = dbusmenu_menuitem_new_with_id(0);
    if (root == NULL) {
        return 1;
    }
    DbusmenuMenuitem *child = dbusmenu_menuitem_new_with_id(101);
    DbusmenuMenuitem *leaf = dbusmenu_menuitem_new_with_id(102);
    if (child == NULL || leaf == NULL) {
        return 2;
    }
    if (!dbusmenu_menuitem_child_append(root, child)) {
        return 3;
    }
    if (!dbusmenu_menuitem_child_append(child, leaf)) {
        return 4;
    }

    /* 2. GList children ordering */
    GList *children = dbusmenu_menuitem_get_children(root);
    if (g_list_length(children) != 1 || (DbusmenuMenuitem *)children->data != child) {
        return 5;
    }
    GList *grand = dbusmenu_menuitem_get_children(child);
    if (g_list_length(grand) != 1 || (DbusmenuMenuitem *)grand->data != leaf) {
        return 6;
    }

    /* 3. property set/get round-trip (typed accessors) */
    if (!dbusmenu_menuitem_property_set(root, DBUSMENU_MENUITEM_PROP_LABEL, "File")) {
        return 7;
    }
    const gchar *label = dbusmenu_menuitem_property_get(root, DBUSMENU_MENUITEM_PROP_LABEL);
    if (label == NULL || strcmp(label, "File") != 0) {
        return 8;
    }
    if (!dbusmenu_menuitem_property_set_bool(child, DBUSMENU_MENUITEM_PROP_ENABLED, TRUE)) {
        return 9;
    }
    if (!dbusmenu_menuitem_property_get_bool(child, DBUSMENU_MENUITEM_PROP_ENABLED)) {
        return 10;
    }

    /* 4. find by id through the tree */
    if (dbusmenu_menuitem_find_id(root, 102) != leaf) {
        return 11;
    }
    if (dbusmenu_menuitem_child_find(child, 102) != leaf) {
        return 12;
    }

    /* 5. parent link */
    if (dbusmenu_menuitem_get_parent(child) != root) {
        return 13;
    }

    /* 6. missing key returns NULL safely. NB: "label" has a registered upstream
     * default ("Label Empty"), so a key without a default is used here. */
    if (dbusmenu_menuitem_property_get(child, "no-such-property") != NULL) {
        return 14;
    }

    g_object_unref(root);
    g_object_unref(child);
    g_object_unref(leaf);
    return 0;
}
