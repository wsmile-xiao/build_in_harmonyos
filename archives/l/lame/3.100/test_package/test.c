#include <stddef.h>
#include <dlfcn.h>
#include <stdio.h>
#ifndef TARGET_SO
#define TARGET_SO "libmp3lame.so"
#endif
int main(void) {
    void *h = dlopen(TARGET_SO, RTLD_NOW | RTLD_GLOBAL);
    if (!h) { fprintf(stderr, "dlopen %s failed: %s\n", TARGET_SO, dlerror()); return 1; }
    /* R34 反空壳：解析并实际调用被测包导出 API，证明库功能可用（非仅加载/符号存在）。 */
    const char *(*get_lame_version)(void) = (const char *(*)(void))dlsym(h, "get_lame_version");
    if (!get_lame_version) { fprintf(stderr, "symbol get_lame_version not found: %s\n", dlerror()); dlclose(h); return 1; }
    const char *ver = get_lame_version();
    if (!ver || !ver[0]) { fprintf(stderr, "get_lame_version() returned empty\n"); dlclose(h); return 1; }
    printf("lame: get_lame_version() = %s\n", ver);
    dlclose(h);
    return 0;
}
