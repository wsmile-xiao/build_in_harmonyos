/* test_libintl.c — libintl 0.26.1 test_package 实质测试（R34）。
 * 加载 libintl.so.8 并校验其同时导出 libintl_* 与 g_libintl_* 两套符号。
 */
#include <dlfcn.h>
#include <stdio.h>

int main(void) {
    void *h = dlopen("libintl.so.8", RTLD_NOW);
    if (!h) {
        printf("dlopen libintl.so.8 FAILED: %s\n", dlerror());
        return 1;
    }
    int ok = 1;
    const char *need[] = {
        "libintl_gettext", "libintl_dgettext", "libintl_bindtextdomain",
        "libintl_textdomain", "g_libintl_gettext", "g_libintl_dgettext",
        "g_libintl_bindtextdomain", "g_libintl_textdomain",
        NULL
    };
    for (int i = 0; need[i]; i++) {
        if (!dlsym(h, need[i])) {
            printf("MISSING symbol: %s\n", need[i]);
            ok = 0;
        }
    }
    dlclose(h);
    if (ok)
        printf("libintl.so.8 exports both libintl_* and g_libintl_*: OK\n");
    return ok ? 0 : 1;
}
