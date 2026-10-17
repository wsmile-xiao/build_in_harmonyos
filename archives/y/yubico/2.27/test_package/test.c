#include <dlfcn.h>
#include <stdio.h>

/*
 * 消费者视角测试（赛道二要求）：模拟"库的使用者"——
 * 以 PAM 运行时的方式 dlopen 加载 pam_yubico.so 模块，
 * 并校验 PAM 模块入口符号存在（pam_sm_authenticate/pam_sm_setcred）。
 * 这是 PAM 模块被系统 PAM 栈加载的真实使用路径。
 */
int main(void) {
    const char *libpath = PAM_MODULE_PATH;
    void *h = dlopen(libpath, RTLD_NOW);
    if (!h) {
        fprintf(stderr, "dlopen %s failed: %s\n", libpath, dlerror());
        return 1;
    }
    if (!dlsym(h, "pam_sm_authenticate")) {
        fprintf(stderr, "symbol pam_sm_authenticate not found: %s\n", dlerror());
        return 2;
    }
    if (!dlsym(h, "pam_sm_setcred")) {
        fprintf(stderr, "symbol pam_sm_setcred not found: %s\n", dlerror());
        return 3;
    }
    printf("dlopen %s OK: pam_sm_authenticate/pam_sm_setcred present\n", libpath);
    return 0;
}
