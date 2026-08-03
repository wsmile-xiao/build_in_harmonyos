#include <gdal.h>
#include <dlfcn.h>
#include <stdio.h>
#include <string.h>

#ifndef TARGET_SO
#define TARGET_SO "libgdal.so"
#endif

int main(void) {
    const char *ver = GDALVersionInfo("RELEASE_NAME");
    if (!ver || !ver[0]) {
        fprintf(stderr, "GDALVersionInfo empty\n");
        return 1;
    }

    GDALAllRegister();
    if (GDALGetDriverCount() <= 0) {
        fprintf(stderr, "GDALGetDriverCount <= 0\n");
        return 1;
    }

    void *handle = dlopen(TARGET_SO, RTLD_NOW);
    if (!handle) {
        fprintf(stderr, "dlopen(%s) failed: %s\n", TARGET_SO, dlerror());
        return 2;
    }
    dlclose(handle);

    printf("gdal ok version=%s drivers=%d\n", ver, GDALGetDriverCount());
    return 0;
}
