#include <proj.h>
#include <dlfcn.h>
#include <stdio.h>
#include <string.h>

#ifndef TARGET_SO
#define TARGET_SO "libproj.so"
#endif

int main(void) {
    PJ_INFO info = proj_info();
    if (!info.version || !info.version[0]) {
        fprintf(stderr, "proj_info version empty\n");
        return 1;
    }

    PJ_CONTEXT *ctx = proj_context_create();
    if (!ctx) {
        fprintf(stderr, "proj_context_create failed\n");
        return 1;
    }

    /* EPSG:4326 identity — exercises DB + API without network. */
    PJ *P = proj_create_crs_to_crs(ctx, "EPSG:4326", "EPSG:4326", NULL);
    if (!P) {
        fprintf(stderr, "proj_create_crs_to_crs failed (PROJ_DATA / proj.db?)\n");
        proj_context_destroy(ctx);
        return 1;
    }
    proj_destroy(P);
    proj_context_destroy(ctx);

    void *handle = dlopen(TARGET_SO, RTLD_NOW);
    if (!handle) {
        fprintf(stderr, "dlopen(%s) failed: %s\n", TARGET_SO, dlerror());
        return 2;
    }
    dlclose(handle);

    printf("proj ok version=%s\n", info.version);
    return 0;
}
