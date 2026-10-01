#include <gpg-error.h>
#include <dlfcn.h>
#include <stdio.h>
#include <string.h>
#ifndef TARGET_SO
#define TARGET_SO "libgpg-error.so"
#endif

/* 鸿蒙特有测试（R34 反空壳）：
 * 在 OHOS 设备上动态加载由本配方构建的 libgpg-error.so，并通过 dlsym 解析并
 * 真实调用其导出 API —— 而非仅加载/打印字符串：
 *   1) gpg_strerror(GPG_ERR_NO_ERROR)           -> 期望 "Success"
 *   2) gpg_strsource(GPG_ERR_SOURCE_ANY)        -> 期望非空（错误源名）
 *   3) gpg_error_check_version(NULL)            -> gpgrt/gpg-error 版本 API，
 *                                                 期望返回非空版本串（"1.61"）
 * 证明库在 OHOS 上 dlopen 可加载、dlsym 可解析、API 可实际执行。
 */
int main(void) {
    void *h = dlopen(TARGET_SO, RTLD_NOW | RTLD_GLOBAL);
    if (!h) {
        fprintf(stderr, "dlopen %s failed: %s\n", TARGET_SO, dlerror());
        return 1;
    }

    /* 1) gpg_strerror */
    const char *(*p_strerror)(gpg_error_t) =
        (const char *(*)(gpg_error_t)) dlsym(h, "gpg_strerror");
    if (!p_strerror) {
        fprintf(stderr, "symbol gpg_strerror not found: %s\n", dlerror());
        dlclose(h);
        return 1;
    }
    const char *s = p_strerror(GPG_ERR_NO_ERROR);
    if (!s || strcmp(s, "Success") != 0) {
        fprintf(stderr, "gpg_strerror(GPG_ERR_NO_ERROR) = '%s' (expected 'Success')\n",
                s ? s : "(null)");
        dlclose(h);
        return 1;
    }
    printf("libgpg-error: gpg_strerror(0)='%s' ok\n", s);

    /* 2) gpg_strsource */
    const char *(*p_strsource)(gpg_error_t) =
        (const char *(*)(gpg_error_t)) dlsym(h, "gpg_strsource");
    if (!p_strsource) {
        fprintf(stderr, "symbol gpg_strsource not found: %s\n", dlerror());
        dlclose(h);
        return 1;
    }
    const char *src = p_strsource(GPG_ERR_SOURCE_ANY);
    if (!src || !*src) {
        fprintf(stderr, "gpg_strsource(GPG_ERR_SOURCE_ANY) empty\n");
        dlclose(h);
        return 1;
    }
    printf("libgpg-error: gpg_strsource(ANY)='%s' ok\n", src);

    /* 3) gpgrt/gpg-error 版本 API（gpg_error_check_version） */
    const char *(*p_ver)(const char *) =
        (const char *(*)(const char *)) dlsym(h, "gpg_error_check_version");
    if (!p_ver) {
        fprintf(stderr, "symbol gpg_error_check_version not found: %s\n", dlerror());
        dlclose(h);
        return 1;
    }
    const char *ver = p_ver(NULL);
    if (!ver || !*ver) {
        fprintf(stderr, "gpg_error_check_version(NULL) returned empty\n");
        dlclose(h);
        return 1;
    }
    printf("libgpg-error: gpg_error_check_version()='%s' ok\n", ver);

    dlclose(h);
    return 0;
}
