#include <dlfcn.h>
#include <stdio.h>

#ifndef TARGET_SO
#define TARGET_SO "libgck-1.so"
#endif

/* R34 反空壳：dlopen 被测包 .so，dlsym 解析真实导出符号，
 * 并实际调用（invoke）无副作用 API 验证 ABI 兼容性与运行时可用性。 */

/* GType 是 glib 的 unsigned long；这里不依赖 glib 头文件，按 ABI 约定使用
 * unsigned long 作为 GType 的等价类型（gcr_certificate_get_type 返回 GType）。 */

/* 解析并调用一个返回 GType（unsigned long）的无参数 API，返回其返回值。 */
static unsigned long call_get_type(void *h, const char *sym) {
    typedef unsigned long (*get_type_fn)(void);
    get_type_fn fn = (get_type_fn)dlsym(h, sym);
    if (!fn) {
        fprintf(stderr, "symbol %s not found: %s\n", sym, dlerror());
        return 0;
    }
    return fn();
}

int main(void) {
    void *h = dlopen(TARGET_SO, RTLD_NOW | RTLD_GLOBAL);
    if (!h) {
        /* 本设备（OHOS/hmdfs+SELinux adhoc 域）可能拒绝 dlopen 本地构建的 .so；
         * 失败时输出原因并返回 2，由 conanfile test() 决定是严格失败还是 ELF 兜底。 */
        fprintf(stderr, "dlopen %s failed: %s\n", TARGET_SO, dlerror());
        return 2;
    }

    /* gck: 实际调用 gck_attribute_get_type()（libgck-1.so 真实导出，返回 GType） */
    if (call_get_type(h, "gck_attribute_get_type") == 0) {
        fprintf(stderr, "gck_attribute_get_type() 调用失败或返回 0\n");
        dlclose(h);
        return 1;
    }
    printf("gcr-base: dlopen %s ok (gck_attribute_get_type invoked)\n", TARGET_SO);
    dlclose(h);

    /* gcr-base 库本体（libgcr-base-3.so）：实际调用 gcr_certificate_get_type() */
    h = dlopen("libgcr-base-3.so", RTLD_NOW | RTLD_GLOBAL);
    if (!h) {
        fprintf(stderr, "dlopen libgcr-base-3.so failed: %s\n", dlerror());
        return 2;
    }
    if (call_get_type(h, "gcr_certificate_get_type") == 0) {
        fprintf(stderr, "gcr_certificate_get_type() 调用失败或返回 0\n");
        dlclose(h);
        return 1;
    }
    printf("gcr-base: dlopen libgcr-base-3.so ok (gcr_certificate_get_type invoked)\n");
    dlclose(h);
    return 0;
}
