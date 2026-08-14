#include <atk/atk.h>
#include <stdio.h>

int main(void) {
    const gchar *version = atk_get_version();
    if (version == NULL) {
        fprintf(stderr, "atk_get_version() returned NULL\n");
        return 1;
    }
    printf("ATK version: %s\n", version);
    printf("ATK library test passed!\n");
    return 0;
}