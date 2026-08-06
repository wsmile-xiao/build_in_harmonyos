#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(void) {
    /* R34: Substantive test - execute the ciso binary and verify output */
    FILE *fp = popen("ciso 2>&1", "r");
    if (!fp) {
        fprintf(stderr, "Failed to run ciso binary\n");
        return 1;
    }

    char buf[256];
    int found = 0;
    while (fgets(buf, sizeof(buf), fp)) {
        if (strstr(buf, "Compressed ISO9660") || strstr(buf, "Usage")) {
            found = 1;
        }
    }
    int rc = pclose(fp);

    if (!found) {
        fprintf(stderr, "ciso did not print expected usage message\n");
        return 1;
    }

    printf("ciso binary test: PASS (exit=%d)\n", rc);
    return 0;
}
