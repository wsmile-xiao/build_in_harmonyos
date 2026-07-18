#include <luv.h>
#include <stdio.h>

int main() {
    const char *version = luv_version();
    if (version == NULL) {
        fprintf(stderr, "luv_version() returned NULL\n");
        return 1;
    }
    printf("Luv version: %s\n", version);
    printf("Luv API test passed!\n");
    return 0;
}
