/* aegean 0.16.0 consumer test — 验证 parseval 二进制已安装且 --help 可执行。
 *
 * aireview P2（R34 反空壳）：原文件为 int main(void){return 0;} 空壳，C 二进制
 * 本身不提供任何验证信号 → 改为 argv 接收 parseval 路径（避依赖 PATH 巧合 +
 * 避 system shell 注入风险），通过 system() 执行 "parseval --help" 并校验退出码，
 * 使 CMake 构建的测试目标具备独立真实验证能力（conanfile.py test() 仍作冗余校验）。
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
/* WIFEXITED/WEXITSTATUS 由 POSIX 定义在 sys/wait.h，OHOS musl libc 可用 */
#include <sys/wait.h>

int main(int argc, char **argv) {
    if (argc != 2) {
        fprintf(stderr, "Usage: %s <parseval binary path>\n", argv[0]);
        return 2;
    }
    const char *bin = argv[1];
    /* shell 注入防御 — 验证路径不含 shell 元字符避注入 */
    if (strpbrk(bin, "\"$;`\\|&")) {
        fprintf(stderr, "FAIL: bin path contains shell metacharacters (injection risk)\n");
        return 3;
    }
    char cmd[8192];
    int sn_ret = snprintf(cmd, sizeof(cmd), "\"%s\" --help > /dev/null 2>&1", bin);
    /* snprintf 截断未检查 — 返值 >=size 表示截断，bin 路径过长致命令截断 */
    if (sn_ret < 0 || (size_t)sn_ret >= sizeof(cmd)) {
        fprintf(stderr, "FAIL: command buffer truncated (snprintf ret %d, buf %zu)\n", sn_ret, sizeof(cmd));
        return 4;
    }
    int ret = system(cmd);
    if (ret != 0) {
        /* system 返 shell 退出码需 WEXITSTATUS 解析真实退出码避误报 */
        int real_code = WIFEXITED(ret) ? WEXITSTATUS(ret) : -1;
        fprintf(stderr, "FAIL: parseval --help exited with code %d (system raw %d%s)\n", real_code, ret,
                 real_code == -1 ? ", WIFEXITED false (killed by signal)" : "");
        return 1;
    }
    printf("aegean smoke test PASSED (parseval --help exit 0)\n");
    return 0;
}
