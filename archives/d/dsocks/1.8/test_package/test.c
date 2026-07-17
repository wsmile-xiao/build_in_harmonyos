/* test_package/test.c — verify dsocks library is loadable and exports expected symbols */
#include <dlfcn.h>
#include <stdio.h>
#include <string.h>

#include "dsocks.h"

int main(void)
{
    /* Test 1: Verify DSOCKS_PATH_LIBC is the OHOS/musl value, not glibc default */
    if (strstr(DSOCKS_PATH_LIBC, "libc.so.6") != NULL) {
        fprintf(stderr, "FAIL: DSOCKS_PATH_LIBC is glibc default (%s), OHOS patch not applied\n", DSOCKS_PATH_LIBC);
        return 1;
    }
    if (strstr(DSOCKS_PATH_LIBC, "libc.so") == NULL) {
        fprintf(stderr, "FAIL: DSOCKS_PATH_LIBC does not contain 'libc.so': %s\n", DSOCKS_PATH_LIBC);
        return 1;
    }
    printf("OK: DSOCKS_PATH_LIBC = %s (OHOS/musl)\n", DSOCKS_PATH_LIBC);

    /* Test 2: Verify the shared library can be loaded via dlopen */
    void *handle = dlopen("libdsocks.so.1", RTLD_LAZY);
    if (!handle) {
        fprintf(stderr, "FAIL: dlopen libdsocks.so.1: %s\n", dlerror());
        return 1;
    }

    /* Test 3: Verify _dsocks_init symbol is exported */
    void *sym = dlsym(handle, "_dsocks_init");
    if (!sym) {
        fprintf(stderr, "FAIL: _dsocks_init not found: %s\n", dlerror());
        dlclose(handle);
        return 1;
    }

    printf("OK: _dsocks_init found at %p\n", sym);
    dlclose(handle);
    return 0;
}
