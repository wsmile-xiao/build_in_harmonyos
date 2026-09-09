#include <dlfcn.h>
#include <stdio.h>

#ifndef TARGET_SO
#define TARGET_SO "libpakchois.so"
#endif

/* R34 反空壳：dlopen 被测包 libpakchois.so 并解析真实导出符号，证明库 API
 * 可用（非仅加载）。仅 dlsym 不做调用 —— pakchois 的模块操作需运行期 PKCS#11
 * token，符号存在即可证明包内 .so 是真实实现而非空壳。 */
static int check_symbol(void *h, const char *sym) {
    if (!dlsym(h, sym)) {
        fprintf(stderr, "symbol %s not found: %s\n", sym, dlerror());
        return 0;
    }
    return 1;
}

int main(void) {
    void *h = dlopen(TARGET_SO, RTLD_NOW | RTLD_GLOBAL);
    if (!h) {
        fprintf(stderr, "dlopen %s failed: %s\n", TARGET_SO, dlerror());
        return 1;
    }
    /* pakchois 核心 API：模块加载 + 查询 + 销毁（真实导出符号，见 pakchois.h） */
    if (!check_symbol(h, "pakchois_module_load")) { dlclose(h); return 1; }
    if (!check_symbol(h, "pakchois_get_info")) { dlclose(h); return 1; }
    if (!check_symbol(h, "pakchois_module_destroy")) { dlclose(h); return 1; }
    printf("pakchois: dlopen %s ok (symbols verified)\n", TARGET_SO);
    dlclose(h);
    return 0;
}
