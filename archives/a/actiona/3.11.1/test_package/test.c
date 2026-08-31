#include <stdio.h>
#include <stdlib.h>
#include <dlfcn.h>

/* actiona test_package：真实调用 actiona API 验证（R34 修复——非空壳）。
 * dlopen 加载 libactiontools.so + dlsym 解析全局 keysym2ucs（nm 确认
 * mangled 符号 _Z10keysym2ucsj——无命名空间，非 ActionTools:: 成员）
 * 并实际调用校验返回值——验证库可加载、
 * 符号存在且 API 行为正确。ACTIONA_LIB_DIR 由 CMakeLists 编译定义注入。 */
int main(void) {
    char path[512];
    snprintf(path, sizeof(path), "%s/actiontools.so", ACTIONA_LIB_DIR);

    void *handle = dlopen(path, RTLD_NOW | RTLD_LOCAL);
    if (!handle) {
        fprintf(stderr, "FAIL: dlopen %s failed: %s\n", path, dlerror());
        return 1;
    }

    /* 解析真实导出符号：keysym2ucs（全局函数，nm 确认 mangled 名 _Z10keysym2ucsj） */
    /* 注：_Z10keysym2ucsj 为无命名空间的全局 keysym2ucs——非 ActionTools:: 成员 */
    unsigned (*keysym2ucs_fn)(unsigned) = (unsigned (*)(unsigned))dlsym(handle, "_Z10keysym2ucsj");
    if (!keysym2ucs_fn) {
        fprintf(stderr, "FAIL: dlsym keysym2ucs failed: %s\n", dlerror());
        dlclose(handle);
        return 1;
    }

    /* 实际调用 API 并校验：keysym 'a'（0x61）应映射回 UCS-2 码点 0x61 */
    unsigned ucs = keysym2ucs_fn(0x61);
    if (ucs != 0x61) {
        fprintf(stderr, "FAIL: keysym2ucs(0x61) = 0x%x (expected 0x61)\n", ucs);
        dlclose(handle);
        return 1;
    }

    printf("test actiona 3.11.1: OK (dlopen %s + dlsym keysym2ucs + call => 0x%x)\n", path, ucs);
    dlclose(handle);
    return 0;
}
