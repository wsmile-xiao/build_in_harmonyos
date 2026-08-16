// test_package/test.c — ldapvi 1.8 消费者测试
// 验证 ldapvi 二进制可执行（--version / --help 非交互退出）。
// 真机/本地已验证：`ldapvi --version` 输出 "ldapvi 1.8" 并退出 0。
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int run_cmd(const char *cmd, const char *needle) {
    char buf[4096];
    FILE *p = popen(cmd, "r");
    if (!p)
        return 0;
    size_t total = 0;
    int found = 0;
    while (fgets(buf, sizeof(buf), p)) {
        total += strlen(buf);
        if (needle && strstr(buf, needle))
            found = 1;
    }
    int rc = pclose(p);
    if (rc == -1)
        return 0;
    /* WIFEXITED && exit code 0 */
    return total > 0 && rc == 0 && (needle == NULL || found);
}

int main(void) {
    int ok = 1;
    ok &= run_cmd("ldapvi --version", "ldapvi");
    ok &= run_cmd("ldapvi --help", "Usage:");
    if (ok) {
        printf("ldapvi smoke test: PASS (binary executable, version+help)\n");
        return 0;
    }
    fprintf(stderr, "FAIL: ldapvi not found or not executable\n");
    return 1;
}
