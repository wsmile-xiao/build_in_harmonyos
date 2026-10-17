#include <dlfcn.h>
#include <stdio.h>

#ifndef TARGET_SO
#define TARGET_SO "libp11-kit.so"
#endif

/* R34 反空壳：dlopen 被测包 .so 并解析真实导出符号，证明库 API 可用（非仅加载）。 */
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
    /* p11-kit 核心 API：模块加载 + 消息处理（真实导出符号） */
    if (!check_symbol(h, "p11_kit_modules_load")) { dlclose(h); return 1; }
    if (!check_symbol(h, "p11_kit_message")) { dlclose(h); return 1; }
    if (!check_symbol(h, "p11_kit_config_option")) { dlclose(h); return 1; }
    printf("p11-kit: dlopen %s ok (symbols verified)\n", TARGET_SO);
    dlclose(h);
    return 0;
}
