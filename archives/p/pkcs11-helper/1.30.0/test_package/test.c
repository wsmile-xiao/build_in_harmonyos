#include <stdio.h>
#include <pkcs11-helper-1.0/pkcs11h-core.h>

int main(void) {
    printf("pkcs11-helper version: %08x\n", pkcs11h_getVersion());
    printf("pkcs11-helper features: %08x\n", pkcs11h_getFeatures());
    return 0;
}
