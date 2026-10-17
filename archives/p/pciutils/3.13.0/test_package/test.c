#include <stdio.h>
#include <pci/pci.h>

int main(void) {
    struct pci_access *pacc = pci_alloc();
    if (!pacc) {
        fprintf(stderr, "Failed to allocate pci_access\n");
        return 1;
    }
    printf("pciutils library version: 0x%06x\n", PCI_LIB_VERSION);
    printf("pci_alloc() succeeded, pacc=%p\n", (void *)pacc);
    pci_cleanup(pacc);
    printf("test pciutils: OK\n");
    return 0;
}
