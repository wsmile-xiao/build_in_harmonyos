/* aj 0.9.9 consumer test — 验证 aj-snapshot 二进制已安装且可执行。
 *
 * R34 反空壳：C 测试二进制通过 system() 真实执行被测包二进制（argv 传
 * aj-snapshot 路径，避依赖 PATH 巧合 + shell 注入防御），校验 usage 输出。
 * 注意：aj-snapshot -h 打印 usage 后返回 1（程序语义，非错误），因此测试
 * 校验输出内容包含 "Usage: aj-snapshot"，退出码允许 0/1。
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
/* WIFEXITED/WEXITSTATUS 由 POSIX 定义在 sys/wait.h，OHOS musl libc 可用 */
#include <sys/wait.h>

int main(int argc, char **argv) {
    if (argc != 2) {
        fprintf(stderr, "Usage: %s <aj-snapshot binary path>\n", argv[0]);
        return 2;
    }
    const char *bin = argv[1];
    /* shell 注入防御 — 验证路径不含 shell 元字符避注入 */
    if (strpbrk(bin, "\"$;`\\|&")) {
        fprintf(stderr, "FAIL: bin path contains shell metacharacters (injection risk)\n");
        return 3;
    }
    char cmd[8192];
    /* OHOS /tmp 为只读文件系统，输出重定向到当前工作目录 */
    int sn_ret = snprintf(cmd, sizeof(cmd), "\"%s\" -h > aj_test_out.txt 2>&1", bin);
    if (sn_ret < 0 || (size_t)sn_ret >= sizeof(cmd)) {
        fprintf(stderr, "FAIL: command buffer truncated (snprintf ret %d, buf %zu)\n", sn_ret, sizeof(cmd));
        return 4;
    }
    int ret = system(cmd);
    /* -h 返回 1 是程序语义（usage 后 return 1），不视为失败 */
    if (!WIFEXITED(ret)) {
        fprintf(stderr, "FAIL: aj-snapshot -h did not exit normally (system raw %d)\n", ret);
        return 1;
    }
    /* 校验 usage 输出内容（文件与重定向一致，写当前工作目录） */
    FILE *fp = fopen("aj_test_out.txt", "r");
    if (!fp) {
        fprintf(stderr, "FAIL: cannot open aj-snapshot output\n");
        return 1;
    }
    char buf[4096];
    size_t n = fread(buf, 1, sizeof(buf) - 1, fp);
    fclose(fp);
    buf[n] = '\0';
    if (n == 0 || !strstr(buf, "Usage: aj-snapshot")) {
        fprintf(stderr, "FAIL: aj-snapshot -h output missing usage text:\n%s\n", buf);
        return 1;
    }
    printf("aj smoke test PASSED (aj-snapshot -h prints usage)\n");
    return 0;
}
