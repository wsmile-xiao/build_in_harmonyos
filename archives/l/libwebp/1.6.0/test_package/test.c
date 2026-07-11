#include <webp/decode.h>
#include <dlfcn.h>
#include <stdio.h>
#ifndef TARGET_SO
#define TARGET_SO "libwebp.so"
#endif
int main(void) {
    void *h = dlopen(TARGET_SO, RTLD_NOW | RTLD_GLOBAL);
    if (!h) { fprintf(stderr, "dlopen %s failed: %s\n", TARGET_SO, dlerror()); return 1; }
    /* R34 反空壳：解析被测包真实导出符号，证明库 API 可用（非仅加载）。 */
    if (!dlsym(h, "WebPGetDecoderVersion")) { fprintf(stderr, "symbol WebPGetDecoderVersion not found: %s\n", dlerror()); dlclose(h); return 1; }
    printf("libwebp: dlopen %s ok\n", TARGET_SO);
    dlclose(h);
    return 0;
}
