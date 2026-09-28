#include <purple.h>

#include <stdio.h>
#include <string.h>

int main(void) {
    const char *version = purple_core_get_version();
    if (version == NULL || strcmp(version, "2.14.14") != 0) {
        fprintf(stderr, "unexpected libpurple version: %s\n", version ? version : "(null)");
        return 1;
    }
    printf("libpurple %s consumer test passed\n", version);
    return 0;
}
