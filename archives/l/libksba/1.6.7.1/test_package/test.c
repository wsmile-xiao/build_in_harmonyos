#include <ksba.h>
#include <dlfcn.h>
#include <stdio.h>
#ifndef TARGET_SO
#define TARGET_SO "libksba.so"
#endif
int main(void) {
    /* ksba.h 编译自检（其 #include <gpg-error.h>，须带上 libgpg-error include）。 */
    gpg_error_t e = 0;
    (void)e;
    void *h = dlopen(TARGET_SO, RTLD_NOW | RTLD_GLOBAL);
    if (!h) { fprintf(stderr, "dlopen %s failed: %s\n", TARGET_SO, dlerror()); return 1; }
    /* R34 反空壳：解析被测包真实导出符号，证明库 API 可用（非仅加载）。 */
    if (!dlsym(h, "ksba_cert_new")) { fprintf(stderr, "symbol ksba_cert_new not found: %s\n", dlerror()); dlclose(h); return 1; }
    if (!dlsym(h, "ksba_cert_release")) { fprintf(stderr, "symbol ksba_cert_release not found: %s\n", dlerror()); dlclose(h); return 1; }
    printf("libksba: dlopen %s ok\n", TARGET_SO);
    dlclose(h);
    return 0;
}
