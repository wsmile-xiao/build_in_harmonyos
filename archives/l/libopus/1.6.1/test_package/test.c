#include <opus/opus.h>
#include <dlfcn.h>
#include <stdio.h>
#include <string.h>
#ifndef TARGET_SO
#define TARGET_SO "libopus.so"
#endif
int main(void) {
    void *h = dlopen(TARGET_SO, RTLD_NOW | RTLD_GLOBAL);
    if (!h) { fprintf(stderr, "dlopen %s failed: %s\n", TARGET_SO, dlerror()); return 1; }
    /* R34 反空壳：不只解析符号，按 opus.h 声明的原型解析后**真正调用** API，
       验证 ① 调用不 crash ② 返回值有效 ③ ABI 匹配（函数指针类型来自被测头）。 */
    typedef const char *(*opus_get_version_string_fn)(void);
    opus_get_version_string_fn get_version =
        (opus_get_version_string_fn)dlsym(h, "opus_get_version_string");
    if (!get_version) { fprintf(stderr, "symbol opus_get_version_string not found: %s\n", dlerror()); dlclose(h); return 1; }
    const char *ver = get_version();
    if (!ver || strncmp(ver, "libopus", 7) != 0) {
        fprintf(stderr, "opus_get_version_string returned unexpected value: %s\n", ver ? ver : "(null)");
        dlclose(h);
        return 1;
    }
    printf("opus: %s (via %s) ok\n", ver, TARGET_SO);
    dlclose(h);
    return 0;
}
