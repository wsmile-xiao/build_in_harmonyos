/* tmpfile-shim.c — OHOS libc tmpfile() 兼容 shim（仅测试期 LD_PRELOAD 注入）。
 *
 * 根因：OHOS musl 的 tmpfile() 硬编码 /tmp，而 HarmonyOS 设备上 /tmp 是只读
 * 挂载 → 恒 EACCES(13) 返回 NULL，且完全无视 TMPDIR 环境变量。
 * tests/test_misc.c:60 把这个 NULL FILE* 直接喂给 libpng（png_init_io），
 * libpng 默认错误处理器 abort → test_misc SIGABRT（exit status 134），
 * 是 15 项上游测试里唯一的失败项。
 * 同根因先例：E272（arm-none-eabi-binutils ctf-compressed）、
 * DRAFT-8959（libei munit）——musl tmpfile() 忽略 TMPDIR。
 *
 * 修复：shim 恢复 POSIX tmpfile() 语义（匿名临时文件：mkstemp 到 $TMPDIR、
 * 立即 unlink、fdopen "w+b"、FD_CLOEXEC），仅在 make check 期 LD_PRELOAD：
 * 不改上游源码、不改测试期望、不进生产 package。库本体（m4ri/*.c）不调用
 * tmpfile()，只有 tests/test_misc.c 这一处使用。
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <unistd.h>
#include <fcntl.h>

FILE *tmpfile(void) {
    const char *d = getenv("TMPDIR");
    if (!d || !*d)
        d = ".";
    char tmpl[512];
    int n = snprintf(tmpl, sizeof(tmpl), "%s/m4ritmpXXXXXX", d);
    if (n < 0 || n >= (int)sizeof(tmpl)) {
        fprintf(stderr, "tmpfile-shim: TMPDIR path too long\n");
        errno = ENAMETOOLONG;
        return NULL;
    }
    int fd = mkstemp(tmpl);
    if (fd < 0) {
        fprintf(stderr, "tmpfile-shim: mkstemp failed in %s: %s\n",
                d, strerror(errno));
        return NULL;
    }
    /* POSIX 2024 / glibc：临时文件 close-on-exec。 */
    (void)fcntl(fd, F_SETFD, FD_CLOEXEC);
    if (unlink(tmpl) < 0) {
        fprintf(stderr, "tmpfile-shim: unlink %s failed: %s\n",
                tmpl, strerror(errno));
        close(fd);
        return NULL;
    }
    FILE *f = fdopen(fd, "w+b");
    if (!f) {
        fprintf(stderr, "tmpfile-shim: fdopen failed: %s\n", strerror(errno));
        close(fd);
        return NULL;
    }
    return f;
}
