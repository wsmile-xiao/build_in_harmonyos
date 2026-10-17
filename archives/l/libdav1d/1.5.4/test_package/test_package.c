#include <dav1d/dav1d.h>
#include <stdio.h>

int main(void) {
    const char *version = dav1d_version();
    if (version == NULL || version[0] == '\0') {
        return 1;
    }
    printf("dav1d version: %s\n", version);
    return 0;
}
