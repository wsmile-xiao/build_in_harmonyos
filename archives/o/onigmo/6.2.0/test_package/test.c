#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <onigmo.h>

int main(void) {
    const char *ver = onig_version();
    if (ver == NULL) {
        if (fprintf(stderr, "onig_version() returned NULL\n") < 0) {
            return 3;
        }
        return 1;
    }
    if (strcmp(ver, "6.2.0") != 0) {
        if (fprintf(stderr, "unexpected Onigmo version: %s\n", ver) < 0) {
            return 3;
        }
        return 2;
    }
    if (printf("Onigmo version: %s\n", ver) < 0) {
        return 3;
    }
    return 0;
}
