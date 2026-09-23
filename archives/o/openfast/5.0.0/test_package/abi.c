#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/*
 * 交付面契约测试（鸿蒙特有视角）：不靠链接器 -lopenfastlib 的隐式解析，而是
 * 按绝对路径以 RTLD_NOW 显式 dlopen 被测包安装出的 libopenfastlib.so——
 * 未解析符号、架构不符、缺 SONAME、代码签名（XPM .codesign）失效等交付面缺陷
 * 都会在此暴露为加载失败；随后逐个 dlsym 解析 C 接口符号。
 *
 * 被测包 lib 目录由 OPENFAST_PACKAGE_LIBDIR 传入，用于保证「加载到的就是被测包那一份」。
 */
static const char *const kSymbols[] = {
    "FAST_AllocateTurbines",
    "FAST_DeallocateTurbines",
    "FAST_Sizes",
};

int main(void)
{
    const char *libdir = getenv("OPENFAST_PACKAGE_LIBDIR");
    char path[4096];
    void *handle;
    const char *err;
    size_t i;

    if (libdir == NULL || libdir[0] == '\0') {
        fprintf(stderr, "FAIL: OPENFAST_PACKAGE_LIBDIR is not set\n");
        return 1;
    }
    if (snprintf(path, sizeof(path), "%s/libopenfastlib.so", libdir) >= (int)sizeof(path)) {
        fprintf(stderr, "FAIL: library path too long\n");
        return 1;
    }

    handle = dlopen(path, RTLD_NOW | RTLD_LOCAL);
    if (handle == NULL) {
        fprintf(stderr, "FAIL: dlopen(%s, RTLD_NOW) -> %s\n", path, dlerror());
        return 1;
    }
    printf("dlopen(%s, RTLD_NOW) OK\n", path);

    for (i = 0; i < sizeof(kSymbols) / sizeof(kSymbols[0]); ++i) {
        dlerror();
        if (dlsym(handle, kSymbols[i]) == NULL) {
            err = dlerror();
            fprintf(stderr, "FAIL: dlsym(%s) -> %s\n", kSymbols[i], err ? err : "NULL symbol");
            return 1;
        }
        printf("dlsym(%s) OK\n", kSymbols[i]);
    }

    if (dlclose(handle) != 0) {
        fprintf(stderr, "FAIL: dlclose -> %s\n", dlerror());
        return 1;
    }

    printf("OpenFAST ABI/loader contract test PASSED (5 assertions)\n");
    return 0;
}
