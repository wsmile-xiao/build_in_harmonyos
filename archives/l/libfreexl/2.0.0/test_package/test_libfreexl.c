#include <freexl.h>

#include <stdio.h>
#include <string.h>

int main(void) {
    const char *version = freexl_version();
    const void *handle = NULL;
    int ret;

    if (version == NULL || strcmp(version, "2.0.0") != 0) {
        fprintf(stderr, "Unexpected libfreexl version: %s\n", version ? version : "NULL");
        return 1;
    }

    ret = freexl_open("definitely-missing-file.xls", &handle);
    if (ret == FREEXL_OK) {
        fprintf(stderr, "freexl_open unexpectedly succeeded on a missing file\n");
        freexl_close(handle);
        return 1;
    }

    if (freexl_close(handle) != FREEXL_OK) {
        fprintf(stderr, "freexl_close failed after open failure: %d\n", ret);
        return 1;
    }

    printf("libfreexl %s open-error handling and close: PASS (open ret=%d)\n", version, ret);
    return 0;
}
