/* test_package/test.c — mlddc 1.0 consumer test
 *
 * mlddc 是 CLI 工具（非库），无可链接库目标；本测试 fork+exec 运行包内
 * mlddc 二进制（路径由 argv[1] 传入，避免依赖 PATH），验证其可执行并
 * 检查无输入时的预期退出码 10（Invalid user data 错误路径，证明程序
 * 本体可运行）。
 */
#include <stdio.h>
#include <stdlib.h>
#include <sys/wait.h>

int main(int argc, char *argv[]) {
    if (argc < 2) {
        printf("test mlddc 1.0: FAIL (missing mlddc path arg)\n");
        return 2;
    }
    /* 运行 mlddc（无输入），重定向输出避免噪音 */
    char cmd[512];
    snprintf(cmd, sizeof(cmd), "%s < /dev/null > /dev/null 2>&1", argv[1]);
    int rc = system(cmd);
    int exit_code = WEXITSTATUS(rc);
    if (exit_code == 10) {
        printf("test mlddc 1.0: OK (expected exit 10 = invalid user data, program runs)\n");
        return 0;
    }
    printf("test mlddc 1.0: FAIL (unexpected exit %d, expected 10)\n", exit_code);
    return 1;
}
