#include <laszip_api.h>
#include <stdio.h>

int main(void) {
    laszip_U8 major = 0;
    laszip_U8 minor = 0;
    laszip_U16 revision = 0;
    laszip_U32 build = 0;

    /* Verify we can call the library API */
    laszip_I32 ret = laszip_get_version(&major, &minor, &revision, &build);
    if (ret != 0) {
        fprintf(stderr, "laszip_get_version failed: %d\n", ret);
        return 1;
    }

    printf("laszip version: %u.%u.%u\n", major, minor, revision);
    if (major != 3) {
        fprintf(stderr, "unexpected major version: %u\n", major);
        return 1;
    }

    /* Verify create/destroy lifecycle */
    laszip_POINTER pointer = NULL;
    ret = laszip_create(&pointer);
    if (ret != 0 || pointer == NULL) {
        fprintf(stderr, "laszip_create failed: %d\n", ret);
        return 1;
    }

    ret = laszip_destroy(pointer);
    if (ret != 0) {
        fprintf(stderr, "laszip_destroy failed: %d\n", ret);
        return 1;
    }

    printf("laszip 3.5.0 API test: OK\n");
    return 0;
}
