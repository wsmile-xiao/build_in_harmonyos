#include <dlfcn.h>
#include <stdio.h>
#include <GLFW/glfw3.h>  /* 编译时依赖 glfw 头文件 (R34) */
#ifndef TARGET_SO
#define TARGET_SO "libglfw.so"
#endif
int main(void) {
    /* 链接时依赖 glfw 库 — 引用 glfwGetVersionString 符号 (R34) */
    const char *ver = glfwGetVersionString();
    printf("glfw version: %s\n", ver ? ver : "(null)");

    void *h = dlopen(TARGET_SO, RTLD_NOW | RTLD_GLOBAL);
    if (!h) { fprintf(stderr, "dlopen %s failed: %s\n", TARGET_SO, dlerror()); return 1; }
    printf("glfw: dlopen %s ok\n", TARGET_SO);
    dlclose(h);
    return 0;
}
