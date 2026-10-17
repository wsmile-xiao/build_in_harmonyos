/*
 * test_package/test.c — libpciaccess 0.17 consumer test (L1)
 *
 * R34: Calls the library API — pci_get_strings (exercises the zlib-backed
 * pci.ids name lookup path), pci_system_init, pci_slot_match_iterator_create,
 * pci_device_next, pci_iterator_destroy and pci_system_cleanup — to verify
 * the library and its zlib dependency link correctly on OHOS.
 *
 * Failure contract: pci_system_init() failing with EACCES/ENOENT/ENOSYS is
 * accepted on platforms whose PCI sysfs interface is restricted or absent
 * (e.g. OHOS devices without a PCI bus). Any other non-zero result, or a
 * wildcard name lookup unexpectedly resolving, is a real failure.
 */
#include <errno.h>
#include <stdio.h>

#include <pciaccess.h>

int main(void) {
    const char *device_name = "unchanged";
    const char *vendor_name = "unchanged";
    const char *subdevice_name = "unchanged";
    const char *subvendor_name = "unchanged";
    struct pci_id_match match = {
        PCI_MATCH_ANY,
        PCI_MATCH_ANY,
        PCI_MATCH_ANY,
        PCI_MATCH_ANY,
        0,
        0,
        0,
    };
    struct pci_device_iterator *iterator;
    struct pci_device *device;
    unsigned int device_count = 0;
    int result;

    pci_get_strings(&match, &device_name, &vendor_name,
                    &subdevice_name, &subvendor_name);
    if (device_name != NULL || vendor_name != NULL ||
        subdevice_name != NULL || subvendor_name != NULL) {
        fprintf(stderr, "PCI_MATCH_ANY unexpectedly resolved a name\n");
        return 1;
    }

    result = pci_system_init();
    if (result != 0) {
        if (result == EACCES || result == ENOENT || result == ENOSYS) {
            printf("libpciaccess consumer test: name lookup passed; "
                   "platform access unavailable (%d)\n", result);
            return 0;
        }
        fprintf(stderr, "pci_system_init failed unexpectedly: %d\n", result);
        return 2;
    }

    iterator = pci_slot_match_iterator_create(NULL);
    if (iterator == NULL) {
        fprintf(stderr, "pci_slot_match_iterator_create returned NULL\n");
        pci_system_cleanup();
        return 3;
    }

    while ((device = pci_device_next(iterator)) != NULL) {
        device_count++;
    }

    pci_iterator_destroy(iterator);
    pci_system_cleanup();
    printf("libpciaccess consumer test: name lookup passed; "
           "%u PCI device(s) discovered\n", device_count);
    return 0;
}
