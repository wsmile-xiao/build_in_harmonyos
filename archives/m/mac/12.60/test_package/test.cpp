// Test package for mac (Monkey's Audio) 12.60
// Verifies that the MAC library can be linked and its API called.
#include <cstdio>
#include "MAC/MACDll.h"

int main(void) {
    // Call a simple C-linkage function from libMAC.so
    const char *ver = GetLibraryVersionString();
    printf("Monkey's Audio library version: %s\n", ver ? ver : "(null)");
    printf("test mac 12.60: OK\n");
    return 0;
}
