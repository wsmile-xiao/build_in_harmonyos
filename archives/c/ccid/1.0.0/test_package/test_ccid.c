/*
    test_ccid.c: 消费者验证 — dlopen libccid.so 并校验 IFD 入口符号
    Copyright (C) 2026  ccid 1.0.0 HarmonyOS adaptation

    pcscd 加载 IFD 驱动时提供宿主符号 log_msg/log_xxd（pcsc-lite ifdhandler 接口）。
    本测试程序模拟宿主，提供 stub 使 libccid.so 可被 dlopen 重定位。
*/
#include <dlfcn.h>
#include <stdarg.h>
#include <stdio.h>

void log_msg(const int priority, const char *fmt, ...) {
    (void)priority; (void)fmt;
}
void log_xxd(const int priority, const char *msg,
             const unsigned char *buffer, const int len) {
    (void)priority; (void)msg; (void)buffer; (void)len;
}

/* ccid 是 pcsc-lite 的 IFD 驱动 bundle，pcscd 在运行期 dlopen 加载。
 * 消费者验证：dlopen 成功 + 关键 IFD 符号（IFDHCreateChannelByName /
 * IFDHControl / IFDHGetCapabilities / IFDHTransmitToICC）解析成功即链路正常。 */
int main(int argc, char **argv) {
    const char *path = (argc > 1) ? argv[1] : "libccid.so";
    void *h = dlopen(path, RTLD_NOW);
    if (!h) {
        printf("dlopen %s FAILED: %s\n", path, dlerror());
        return 1;
    }
    const char *syms[] = {
        "IFDHCreateChannelByName", "IFDHControl",
        "IFDHGetCapabilities", "IFDHTransmitToICC", "IFDHCloseChannel", NULL
    };
    int missing = 0;
    for (int i = 0; syms[i]; i++) {
        if (!dlsym(h, syms[i])) {
            printf("missing symbol: %s\n", syms[i]);
            missing++;
        }
    }
    dlclose(h);
    if (missing) {
        printf("ccid 1.0.0 FAILED: %d IFD symbols missing\n", missing);
        return 1;
    }
    printf("ccid 1.0.0 OK: dlopen + IFD symbols verified\n");
    return 0;
}
