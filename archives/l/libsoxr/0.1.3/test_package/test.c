#include <stdint.h>
#include <stddef.h>
#include <soxr.h>
#include <dlfcn.h>
#include <stdio.h>
#ifndef TARGET_SO
#define TARGET_SO "libsoxr.so"
#endif
int main(void) {
    void *h = dlopen(TARGET_SO, RTLD_NOW | RTLD_GLOBAL);
    if (!h) { fprintf(stderr, "dlopen %s failed: %s\n", TARGET_SO, dlerror()); return 1; }
    /* R34 反空壳：解析并实际调用被测包 API，证明库函数可执行（非仅符号存在）。 */
    char const * (*soxr_version_fn)(void) =
        (char const * (*)(void)) dlsym(h, "soxr_version");
    if (!soxr_version_fn) { fprintf(stderr, "symbol soxr_version not found: %s\n", dlerror()); dlclose(h); return 1; }
    char const *ver = soxr_version_fn();
    if (!ver) { fprintf(stderr, "soxr_version() returned NULL\n"); dlclose(h); return 1; }
    printf("libsoxr: dlopen %s ok, soxr_version=%s\n", TARGET_SO, ver);
    dlclose(h);
    return 0;
}
