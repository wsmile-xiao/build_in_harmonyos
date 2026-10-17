#include <dlfcn.h>
#include <stdio.h>
#include <string.h>
#ifndef TARGET_SO
#define TARGET_SO "libzstd.so"
#endif
int main(void) {
    /* R34 anti-empty-shell: dlopen libzstd.so + dlsym real ZSTD API symbols */
    void *h = dlopen(TARGET_SO, RTLD_NOW | RTLD_GLOBAL);
    if (!h) { fprintf(stderr, "dlopen %s failed: %s\n", TARGET_SO, dlerror()); return 1; }

    /* Verify ZSTD_versionNumber is exported and callable */
    unsigned (*p_version)(void) = (unsigned (*)(void))dlsym(h, "ZSTD_versionNumber");
    if (!p_version) { fprintf(stderr, "symbol ZSTD_versionNumber not found: %s\n", dlerror()); dlclose(h); return 1; }

    unsigned v = p_version();
    if (v < 10000) { fprintf(stderr, "ZSTD_versionNumber=%u too low\n", v); dlclose(h); return 1; }

    /* Verify ZSTD_compress is exported */
    if (!dlsym(h, "ZSTD_compress")) { fprintf(stderr, "symbol ZSTD_compress not found: %s\n", dlerror()); dlclose(h); return 1; }

    printf("zstd: version=%u, dlopen %s ok\n", v, TARGET_SO);
    dlclose(h);
    return 0;
}