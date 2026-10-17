// test_package/test.c — dnsmap 消费者测试
// 验证 dnsmap 二进制存在且可执行（-h 帮助输出）。
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/wait.h>

int main(void) {
    // dnsmap 无 API（命令行工具），验证二进制可执行
    // 通过 system() 运行 dnsmap -h（无参数用法输出）
    int rc = system("dnsmap -h > /dev/null 2>&1");
    // -h 可能返回非 0（无参数），能执行即通过（127 = command not found）
    // system() 返回 waitpid 格式状态（127<<8==32512），需 WEXITSTATUS 解析；
    // rc == -1 覆盖 fork 失败
    if (rc == -1 || WEXITSTATUS(rc) == 127) {
        fprintf(stderr, "FAIL: dnsmap not found or not executable\n");
        return 1;
    }
    printf("dnsmap smoke test: PASS (binary executable)\n");
    return 0;
}
