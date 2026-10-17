/* R34 反空壳测试：dlopen libvoikko.so 后解析并真实调用被测包导出的 C API。
 *
 * libvoikko 4.x 没有内置词典路径，运行期需要单独的 voikko-fi 词典数据。
 * 在没有词典的环境里，voikkoInit 必须优雅失败并返回错误信息，而不是崩溃或
 * 返回句柄。本测试即走这条真实初始化路径：加载库 -> 解析 voikkoInit 符号 ->
 * 以 "fi" 初始化 -> 断言正确失败且错误信息非空。
 */
#include <dlfcn.h>
#include <stdio.h>
#include <string.h>

#ifndef TARGET_SO
#define TARGET_SO "libvoikko.so"
#endif

/* 不透明句柄，仅作占位 */
struct VoikkoHandle;

int main(void) {
    void *h = dlopen(TARGET_SO, RTLD_NOW | RTLD_GLOBAL);
    if (!h) {
        fprintf(stderr, "dlopen %s failed: %s\n", TARGET_SO, dlerror());
        return 1;
    }

    void *(*voikkoInit_fn)(const char **, const char *, const char *) =
        (void *(*)(const char **, const char *, const char *))dlsym(h, "voikkoInit");
    if (!voikkoInit_fn) {
        fprintf(stderr, "symbol voikkoInit not found: %s\n", dlerror());
        dlclose(h);
        return 1;
    }

    void (*voikkoTerminate_fn)(struct VoikkoHandle *) =
        (void (*)(struct VoikkoHandle *))dlsym(h, "voikkoTerminate");
    if (!voikkoTerminate_fn) {
        fprintf(stderr, "symbol voikkoTerminate not found: %s\n", dlerror());
        dlclose(h);
        return 1;
    }

    /* 断言 1：无词典时 voikkoInit 必须返回 NULL 句柄 */
    const char *err = NULL;
    struct VoikkoHandle *handle =
        (struct VoikkoHandle *)voikkoInit_fn(&err, "fi", NULL);
    if (handle != NULL) {
        fprintf(stderr, "unexpected: voikkoInit succeeded without any dictionary\n");
        voikkoTerminate_fn(handle);
        dlclose(h);
        return 1;
    }

    /* 断言 2：失败时必须给出非空错误信息 */
    if (err == NULL || err[0] == '\0') {
        fprintf(stderr, "voikkoInit failed but error message is empty\n");
        dlclose(h);
        return 1;
    }

    printf("libvoikko: voikkoInit(\"fi\") correctly failed without dictionary: %s\n", err);

    dlclose(h);
    printf("libvoikko smoke OK\n");
    return 0;
}
