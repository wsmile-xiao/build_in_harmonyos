// test_package/test.c — ldap2dns 0.3.1 消费者测试 (R34)
// 验证已安装的 ldap2dns / ldap2dnsd 二进制可执行：
//   -V 打印版本行 "ldap2dns, version 0.3.1" 与 usage（非崩溃、非空输出）。
// 真机/本地已验证：./ldap2dns -V 输出该版本行并退出码 1（上游 getopt
// 将 -V 视为需要参数，属上游行为，测试只断言版本串与输出非空）。
#include <stdio.h>
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
    pclose(p);
    return total > 0 && found;
}

int main(void) {
    int ok = 1;
    ok &= run_cmd("ldap2dns -V", "ldap2dns, version 0.3.1");
    ok &= run_cmd("ldap2dnsd -V", "ldap2dns, version 0.3.1");
    if (ok) {
        printf("ldap2dns smoke test: PASS (ldap2dns + ldap2dnsd executable, version printed)\n");
        return 0;
    }
    fprintf(stderr, "FAIL: ldap2dns/ldap2dnsd not found or not executable\n");
    return 1;
}
