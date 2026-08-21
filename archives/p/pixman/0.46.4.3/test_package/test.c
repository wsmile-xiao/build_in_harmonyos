#include <pixman-1/pixman.h>
#include <dlfcn.h>
#include <stdio.h>
#ifndef TARGET_SO
#define TARGET_SO "libpixman-1.so"
#endif
typedef const char *(*version_fn)(void);
int main(void) {
    void *h = dlopen(TARGET_SO, RTLD_NOW | RTLD_GLOBAL);
    if (!h) { fprintf(stderr, "dlopen %s failed: %s\n", TARGET_SO, dlerror()); return 1; }
    version_fn pixman_version = (version_fn)dlsym(h, "pixman_version_string");
    if (!pixman_version) { fprintf(stderr, "dlsym pixman_version_string failed: %s\n", dlerror()); dlclose(h); return 2; }
    const char *ver = pixman_version();
    if (!ver || !*ver) { fprintf(stderr, "pixman_version_string returned empty\n"); dlclose(h); return 3; }
    printf("pixman %s: dlopen %s ok\n", ver, TARGET_SO);
    dlclose(h);
    return 0;
}
