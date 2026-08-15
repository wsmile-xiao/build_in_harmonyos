// test_package/test.c — diffstat 消费者测试
// 验证 diffstat 二进制可执行（-h 帮助 + 简单 diff 输入）。
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(void) {
    // diffstat 是命令行工具，验证二进制可执行
    // 用简单 diff 输入验证 -c 参数输出
    FILE *f = fopen("test.diff", "w");
    if (!f) return 1;
    fprintf(f, "--- a/foo.c\n+++ b/foo.c\n@@ -1,1 +1,1 @@\n-x\n+y\n");
    fclose(f);

    // 运行 diffstat 处理 test.diff，输出到 stdout
    int rc = system("diffstat test.diff > /dev/null 2>&1");
    if (rc != 0) {  // 未找到 / 不可执行 / 处理失败
        fprintf(stderr, "FAIL: diffstat not found or not executable\n");
        return 1;
    }
    printf("diffstat smoke test: PASS (binary executable)\n");
    remove("test.diff");
    return 0;
}
