/* test_alfred.c — alfred 2026.2 consumer test — 验证 alfred 二进制可执行。
 *
 * AI review P2（R34 反空壳）：原文件为 int main(void){return 0;} 空壳，
 * C 二进制本身不提供任何验证信号 → 改为 argv 接收 alfred 路径（避依赖
 * PATH 巧合 + 避 shell 注入风险），通过 popen() 执行 "alfred --help" 并
 * 校验输出含 usage 特征串，使 CMake 构建的测试目标具备独立真实验证能力
 * （conanfile.py test() 仍作冗余校验）。
 *
 * 注意：alfred --help 打印 usage 后退出码非 0 属预期行为（PR 已确认），
 * 故不校验退出码 0，只校验进程正常退出（WIFEXITED）且输出含特征串。
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
/* WIFEXITED/WEXITSTATUS 由 POSIX 定义在 sys/wait.h，OHOS musl libc 可用 */
#include <sys/wait.h>

int main(int argc, char **argv) {
    if (argc != 2) {
        fprintf(stderr, "Usage: %s <alfred binary path>\n", argv[0]);
        return 2;
    }
    const char *bin = argv[1];
    /* shell 注入防御 — 验证路径不含 shell 元字符避注入 */
    if (strpbrk(bin, "\"$;`\\|&")) {
        fprintf(stderr, "FAIL: bin path contains shell metacharacters (injection risk)\n");
        return 3;
    }
    char cmd[8192];
    int sn_ret = snprintf(cmd, sizeof(cmd), "\"%s\" --help 2>&1", bin);
    /* snprintf 截断未检查 — 返值 >=size 表示截断，bin 路径过长致命令截断 */
    if (sn_ret < 0 || (size_t)sn_ret >= sizeof(cmd)) {
        fprintf(stderr, "FAIL: command buffer truncated (snprintf ret %d, buf %zu)\n", sn_ret, sizeof(cmd));
        return 4;
    }
    FILE *fp = popen(cmd, "r");
    if (!fp) {
        fprintf(stderr, "FAIL: popen failed for %s\n", cmd);
        return 5;
    }
    char out[8192];
    size_t n = fread(out, 1, sizeof(out) - 1, fp);
    out[n] = '\0';
    int st = pclose(fp);
    /* alfred --help 退出码非 0 属预期；只要求进程正常退出（未被信号杀死） */
    if (!WIFEXITED(st)) {
        fprintf(stderr, "FAIL: alfred --help killed by signal (raw %d)\n", st);
        return 1;
    }
    /* 校验输出包含 usage 特征串，确认确实是 alfred 而非空壳 */
    if (!strstr(out, "Usage") && !strstr(out, "alfred")) {
        fprintf(stderr, "FAIL: alfred --help output missing 'Usage'/'alfred' markers:\n%s\n", out);
        return 1;
    }
    printf("alfred smoke test PASSED (alfred --help output verified)\n");
    return 0;
}
