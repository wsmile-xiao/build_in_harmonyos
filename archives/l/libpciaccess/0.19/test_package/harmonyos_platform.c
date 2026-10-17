#include <errno.h>
#include <stdio.h>

#include <pciaccess.h>

int main(void) {
    struct pci_id_match match = {
        PCI_MATCH_ANY,
        PCI_MATCH_ANY,
        PCI_MATCH_ANY,
        PCI_MATCH_ANY,
        0,
        0,
        0,
    };
    const char *device_name = "unset";
    const char *vendor_name = "unset";
    const char *subdevice_name = "unset";
    const char *subvendor_name = "unset";
    int result;

    pci_get_strings(&match, &device_name, &vendor_name,
                    &subdevice_name, &subvendor_name);
    if (device_name != NULL || vendor_name != NULL ||
        subdevice_name != NULL || subvendor_name != NULL) {
        fprintf(stderr, "HarmonyOS PCI wildcard lookup returned a name\n");
        return 1;
    }

    result = pci_system_init();
    if (result == 0) {
        pci_system_cleanup();
        puts("libpciaccess HarmonyOS platform test: PCI backend available");
        return 0;
    }

    if (result == EACCES || result == ENOENT || result == ENOSYS) {
        printf("libpciaccess HarmonyOS platform test: restricted PCI access "
               "accepted (%d)\n", result);
        return 0;
    }

    fprintf(stderr, "unexpected HarmonyOS PCI initialization error: %d\n", result);
    return 2;
}
