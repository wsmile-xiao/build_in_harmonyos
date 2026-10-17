#include <zstd.h>
#include <dlfcn.h>
#include <stdio.h>
#ifndef TARGET_SO
#define TARGET_SO "libzstd.so"
#endif
int main(void) {
    void *h = dlopen(TARGET_SO, RTLD_NOW | RTLD_GLOBAL);
    if (!h) { fprintf(stderr, "dlopen %s failed: %s\n", TARGET_SO, dlerror()); return 1; }
    /* R34 反空壳：dlsym 后实际调用 ZSTD_versionNumber() 并校验返回值，
       证明被测包 API 可执行（非仅符号存在），可捕获 ABI 不兼容/运行时崩溃。 */
    unsigned (*ver_fn)(void) = (unsigned (*)(void))dlsym(h, "ZSTD_versionNumber");
    if (!ver_fn) { fprintf(stderr, "symbol ZSTD_versionNumber not found: %s\n", dlerror()); dlclose(h); return 1; }
    unsigned ver = ver_fn();
    if (ver == 0) { fprintf(stderr, "ZSTD_versionNumber returned 0\n"); dlclose(h); return 1; }
    printf("zstd: dlopen %s ok, version %u\n", TARGET_SO, ver);
    dlclose(h);
    return 0;
}
