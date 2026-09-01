/* test.c — R34: Verify libmsi library linking and API callable.
 *
 * Includes the conan-installed libmsi header to verify:
 * 1. Header files are correctly installed in the package
 * 2. Library symbols are resolved (linking succeeded)
 * 3. GObject type system is initialized (type registered)
 */
#include <stdio.h>
#include <libmsi-1.0/libmsi-database.h>

int main(void) {
    GType gtype = libmsi_database_get_type();
    if (gtype == 0) {
        printf("FAIL: libmsi_database_get_type() returned 0\n");
        return 1;
    }
    printf("PASS: libmsi database type registered (GType=%lu)\n", (unsigned long)gtype);
    return 0;
}
