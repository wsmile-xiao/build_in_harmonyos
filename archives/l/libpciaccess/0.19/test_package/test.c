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
        (void)pci_device_is_boot_display(device);
        device_count++;
    }

    pci_iterator_destroy(iterator);
    pci_system_cleanup();
    printf("libpciaccess consumer test: name lookup passed; "
           "%u PCI device(s) discovered\n", device_count);
    return 0;
}
