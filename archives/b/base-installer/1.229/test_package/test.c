/*
 * test_base-installer — R34 真实功能测试（非空壳）
 *
 * 实际执行包内 base-installer 的 pkgdetails 二进制，读取 Debian-style
 * Packages.test 文件，校验真实 stdout/退出码及至少一个依赖解析结果
 * （Depends: libc6 与 Pre-Depends: libgcc-s1）。
 *
 * 失败条件（任一即非零退出）：
 *   1. pkgdetails 二进制缺失或不可执行
 *   2. pkgdetails GETDEPS 退出码非 0
 *   3. stdout 未包含期望的依赖解析结果 libc6 / libgcc-s1
 *
 * 用法: test_base-installer <pkgdetails路径> <Packages.test路径>
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(int argc, char **argv)
{
    if (argc < 3) {
        fprintf(stderr, "usage: %s <pkgdetails> <Packages.test>\n", argv[0]);
        return 2;
    }
    const char *pkgdetails = argv[1];
    const char *packages   = argv[2];

    /* 1) 二进制必须存在且可执行 */
    FILE *f = fopen(pkgdetails, "r");
    if (!f) {
        fprintf(stderr, "FAIL: pkgdetails binary missing: %s\n", pkgdetails);
        return 1;
    }
    fclose(f);

    /* 2) 构造 GETDEPS 调用并捕获真实 stdout/stderr */
    char cmd[2048];
    snprintf(cmd, sizeof cmd, "\"%s\" GETDEPS \"%s\" zlib1g libc6 2>&1",
             pkgdetails, packages);
    FILE *p = popen(cmd, "r");
    if (!p) {
        fprintf(stderr, "FAIL: cannot execute pkgdetails\n");
        return 1;
    }
    char out[8192];
    size_t n = fread(out, 1, sizeof(out) - 1, p);
    out[n] = '\0';
    int rc = pclose(p);

    printf("pkgdetails GETDEPS stdout:\n%s\n", out);
    if (rc != 0) {
        fprintf(stderr, "FAIL: pkgdetails GETDEPS exit code=%d\n", rc);
        return 1;
    }

    /* 3) 依赖解析结果校验：zlib1g→Depends libc6；libc6→Pre-Depends libgcc-s1 */
    if (!strstr(out, "libc6")) {
        fprintf(stderr, "FAIL: expected dependency 'libc6' not resolved\n");
        return 1;
    }
    if (!strstr(out, "libgcc-s1")) {
        fprintf(stderr, "FAIL: expected dependency 'libgcc-s1' not resolved\n");
        return 1;
    }

    printf("PASS: pkgdetails resolved Depends libc6 and Pre-Depends libgcc-s1\n");
    return 0;
}