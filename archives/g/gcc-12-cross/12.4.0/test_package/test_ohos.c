#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#include <features.h>
#include <sys/utsname.h>

/* HarmonyOS 专项测试：验证 GCC 12.4.0 交叉编译器针对 aarch64-linux-ohos
   目标的平台宏、64 位 ABI 与运行时（uname 系统面），并实际运行于 OHOS 设备。 */

#if !defined(__OHOS__)
#error "aarch64-linux-ohos target must define __OHOS__"
#endif

#if !defined(__aarch64__)
#error "aarch64-linux-ohos target must define __aarch64__"
#endif

#if __SIZEOF_POINTER__ != 8
#error "OHOS aarch64 target must be 64-bit (LP64)"
#endif

int main(void)
{
    struct utsname u;
    char buf[128];
    int musl = 0;

#ifdef __MUSL__
    musl = 1;
#endif

    /* OHOS 系统调用面：uname 必须可用并返回非空 sysname */
    if (uname(&u) != 0 || u.sysname[0] == '\0') {
        return 2;
    }

    snprintf(buf, sizeof(buf), "ohos-uname:%s/%s musl:%d gcc12-ok",
             u.sysname, u.release, musl);
    if (strncmp(buf, "ohos-uname:", 11) != 0) {
        return 3;
    }
    puts(buf);
    return 0;
}