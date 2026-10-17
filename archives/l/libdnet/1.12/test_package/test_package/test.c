#include <stdio.h>
#include <string.h>
#include <dnet.h>

int main(void) {
    struct addr a;
    char *str;
    int ret;

    /* Test addr_pton: parse "127.0.0.1" into addr struct */
    ret = addr_pton("127.0.0.1", &a);
    if (ret != 0) {
        fprintf(stderr, "addr_pton failed: %d\n", ret);
        return 1;
    }

    /* Test addr_ntoa: convert addr back to string */
    str = addr_ntoa(&a);
    if (str == NULL) {
        fprintf(stderr, "addr_ntoa returned NULL\n");
        return 1;
    }

    printf("addr_ntoa: %s\n", str);

    /* Verify round-trip conversion */
    if (strcmp(str, "127.0.0.1") != 0) {
        fprintf(stderr, "round-trip mismatch: got %s, expected 127.0.0.1\n", str);
        return 1;
    }

    printf("libdnet addr_pton/addr_ntoa round-trip test: OK\n");
    return 0;
}
