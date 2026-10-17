/* test_package/test.c — libseccomp 2.6.0 consumer test (L1)
 *
 * L1 test:
 * 1. 链接 libseccomp 并调用 seccomp_init()/seccomp_release()——
 *    真实调用库 API 验证库可用；
 * 2. seccomp_syscall_resolve_name("read") 验证 syscall 表正确生成
 *    （gperf 表 + aarch64 架构支持）。
 */
#include <seccomp.h>
#include <stdio.h>

int main(void) {
    /* 初始化 seccomp 过滤器上下文（SCMP_ACT_ALLOW 默认放行） */
    scmp_filter_ctx ctx = seccomp_init(SCMP_ACT_ALLOW);
    if (ctx == NULL) {
        fprintf(stderr, "libseccomp test FAILED: seccomp_init returned NULL\n");
        return 1;
    }
    /* 验证 syscall 表（gperf 生成 + aarch64 表）：read() 必须能解析 */
    int syscall_nr = seccomp_syscall_resolve_name("read");
    if (syscall_nr <= 0) {
        fprintf(stderr, "libseccomp test FAILED: "
                        "seccomp_syscall_resolve_name(read) = %d\n",
                syscall_nr);
        seccomp_release(ctx);
        return 1;
    }
    seccomp_release(ctx);
    printf("libseccomp 2.6.0 consumer test OK "
           "(seccomp_init/release, read=%d)\n", syscall_nr);
    return 0;
}
