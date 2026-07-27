#include <stdio.h>
#include <string.h>
#include <libtasn1.h>

int main(void) {
    const char *version = asn1_check_version(NULL);
    if (version == NULL) {
        fprintf(stderr, "FAIL: asn1_check_version returned NULL\n");
        return 1;
    }
    if (strcmp(version, ASN1_VERSION) != 0) {
        fprintf(stderr, "FAIL: version mismatch: %s != %s\n", version, ASN1_VERSION);
        return 1;
    }
    printf("libtasn1 version: %s\n", version);
    printf("test PASSED\n");
    return 0;
}
