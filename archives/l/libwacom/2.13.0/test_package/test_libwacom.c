// libwacom 2.13.0 consumer test (R34: exercises real API).
// Loads the shipped tablet database through
// libwacom_database_new_for_path() (the DB directory is passed by the
// test_package conanfile via argv[1]; libwacom_database_new() without
// arguments only probes the prefix baked in at library build time),
// enumerates known devices and looks up a known tablet by name.
#include <libwacom/libwacom.h>

#include <stdio.h>
#include <string.h>

int main(int argc, char **argv)
{
    if (argc < 2) {
        fprintf(stderr, "usage: test_libwacom <db-dir>\n");
        return 1;
    }
    WacomError *error = libwacom_error_new();
    WacomDeviceDatabase *db = libwacom_database_new_for_path(argv[1]);
    if (!db) {
        fprintf(stderr, "FAIL: libwacom_database_new_for_path(%s) returned NULL\n",
                argv[1]);
        libwacom_error_free(&error);
        return 1;
    }

    // The database must know at least one device (the shipped .tablet
    // files parse and are loadable).
    WacomDevice **devices =
        libwacom_list_devices_from_database(db, error);
    if (!devices || !devices[0]) {
        fprintf(stderr, "FAIL: database lists no devices (%s)\n",
                libwacom_error_get_message(error));
        libwacom_database_destroy(db);
        libwacom_error_free(&error);
        return 1;
    }
    int n = 0;
    while (devices[n])
        n++;
    printf("database lists %d devices\n", n);

    // Device lookup by known name: "Wacom Intuos4 6x9" is in the
    // upstream data files.
    WacomDevice *dev = libwacom_new_from_name(db, "Wacom Intuos4 6x9", error);
    if (!dev) {
        fprintf(stderr, "FAIL: known tablet 'Wacom Intuos4 6x9' not found (%s)\n",
                libwacom_error_get_message(error));
        libwacom_database_destroy(db);
        libwacom_error_free(&error);
        return 1;
    }

    int vendor = libwacom_get_vendor_id(dev);
    int product = libwacom_get_product_id(dev);
    if (vendor == 0 || product == 0) {
        fprintf(stderr, "FAIL: vendor/product ids are zero\n");
        libwacom_destroy(dev);
        libwacom_database_destroy(db);
        libwacom_error_free(&error);
        return 1;
    }

    printf("PASS: db=%d devices, Intuos4 6x9 -> %04x:%04x\n",
           n, (unsigned)vendor, (unsigned)product);
    libwacom_destroy(dev);
    libwacom_database_destroy(db);
    libwacom_error_free(&error);
    return 0;
}
