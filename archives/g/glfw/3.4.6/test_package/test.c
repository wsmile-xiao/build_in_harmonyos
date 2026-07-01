#include <dlfcn.h>
#include <stdio.h>

#ifndef TARGET_SO
#define TARGET_SO "libglfw.so"
#endif

int main(void) {
    /* 运行期验证：dlopen 目标库 .so（库名由 build 时从依赖 cpp_info.libs 注入，仅设备原生运行时执行） */
    void *h = dlopen(TARGET_SO, RTLD_NOW | RTLD_GLOBAL);
    if (!h) {
        fprintf(stderr, "dlopen failed: %s\n", dlerror());
        return 1;
    }
    printf("dlopen %s ok\n", TARGET_SO);
    dlclose(h);
    return 0;
}
