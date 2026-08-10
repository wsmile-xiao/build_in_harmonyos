#include <ag-manager.h>
#include <ag-account.h>
#include <glib.h>
#include <stdio.h>

int main(void) {
    /* Test 1: Verify library type system is initialized.
     * AG_TYPE_MANAGER is a GType constant that requires the library
     * to be properly linked and the GObject type system to work. */
    GType manager_type = AG_TYPE_MANAGER;
    if (manager_type == 0) {
        fprintf(stderr, "FAIL: AG_TYPE_MANAGER is 0\n");
        return 1;
    }
    g_print("OK: AG_TYPE_MANAGER = %lu\n", manager_type);

    /* Test 2: Verify AgAccount type is available */
    GType account_type = AG_TYPE_ACCOUNT;
    if (account_type == 0) {
        fprintf(stderr, "FAIL: AG_TYPE_ACCOUNT is 0\n");
        return 1;
    }
    g_print("OK: AG_TYPE_ACCOUNT = %lu\n", account_type);

    /* Test 3: Verify the types are different (sanity check) */
    if (manager_type == account_type) {
        fprintf(stderr, "FAIL: manager and account types are the same\n");
        return 1;
    }
    g_print("OK: types are distinct\n");

    /* Test 4: Verify G_TYPE_OBJECT is the parent of AgManager */
    GType parent = g_type_parent(manager_type);
    if (parent != G_TYPE_OBJECT) {
        fprintf(stderr, "FAIL: AG_TYPE_MANAGER parent is not G_TYPE_OBJECT\n");
        return 1;
    }
    g_print("OK: AG_TYPE_MANAGER inherits from G_TYPE_OBJECT\n");

    g_print("All tests passed.\n");
    return 0;
}
