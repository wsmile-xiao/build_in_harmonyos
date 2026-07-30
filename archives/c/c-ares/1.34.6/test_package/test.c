#include <stdio.h>
#include <stdlib.h>
#include <ares.h>

int main(void) {
    int status = ares_library_init(ARES_LIB_INIT_ALL);
    if (status != ARES_SUCCESS) {
        fprintf(stderr, "ares_library_init failed: %s\n", ares_strerror(status));
        return 1;
    }
    printf("c-ares version: %s\n", ares_version(NULL));
    ares_library_cleanup();
    printf("test c-ares 1.34.6: OK\n");
    return 0;
}
