/* test_package/test.c — kexec-tools 2.0.32 消费者测试
 *
 * kexec-tools 是纯命令行工具包（无链接库），消费者验证口径为
 * "工具构建可用性"：定位包内 kexec/vmcore-dmesg 二进制并实际执行，
 * 断言版本输出与错误路径行为（与 test_package/conanfile.py::test()
 * 的 Python 侧验证互补——本 C 侧通过 system() 驱动同一组断言）。
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int run_cmd(const char *cmd, char *out, size_t outsz) {
    FILE *p = popen(cmd, "r");
    if (!p) return -1;
    out[0] = '\0';
    size_t n = fread(out, 1, outsz - 1, p);
    out[n] = '\0';
    int rc = pclose(p);
    return rc;
}

int main(int argc, char **argv) {
    /* argv[1] = 包内 bin 目录（由 CMake 传入 KEXEC_BIN_DIR 或 conanrunenv） */
    char buf[8192];
    char cmd[1024];
    int failures = 0;

    const char *bindir = (argc > 1) ? argv[1] : getenv("KEXEC_BIN_DIR");
    if (!bindir || !bindir[0]) {
        /* 回退：从 PATH 或默认布局找 */
        bindir = "/usr/local/bin";
    }

    /* 断言 1：kexec --version 输出版本号 */
    snprintf(cmd, sizeof(cmd), "%s/kexec --version 2>&1", bindir);
    run_cmd(cmd, buf, sizeof(buf));
    if (strstr(buf, "kexec-tools 2.0.32") == NULL) {
        fprintf(stderr, "FAIL: kexec --version output unexpected: %s\n", buf);
        failures++;
    } else {
        printf("PASS: kexec --version -> kexec-tools 2.0.32\n");
    }

    /* 断言 2：kexec --help 输出用法（选项解析器工作） */
    snprintf(cmd, sizeof(cmd), "%s/kexec --help 2>&1", bindir);
    run_cmd(cmd, buf, sizeof(buf));
    if (strstr(buf, "Usage") == NULL) {
        fprintf(stderr, "FAIL: kexec --help no usage output\n");
        failures++;
    } else {
        printf("PASS: kexec --help prints usage\n");
    }

    /* 断言 3：vmcore-dmesg 错误路径（ELF 加载 + libc IO 正常；
     * OHOS 内核无 kexec_load syscall，真实加载属运行时内核依赖，
     * 故以工具构建可用性为验证口径） */
    snprintf(cmd, sizeof(cmd), "%s/vmcore-dmesg /no/such/vmcore/file 2>&1", bindir);
    run_cmd(cmd, buf, sizeof(buf));
    if (strstr(buf, "Cannot open") == NULL) {
        fprintf(stderr, "FAIL: vmcore-dmesg unexpected output: %s\n", buf);
        failures++;
    } else {
        printf("PASS: vmcore-dmesg error path works\n");
    }

    if (failures) {
        fprintf(stderr, "%d assertion(s) failed\n", failures);
        return 1;
    }
    printf("test_kexec_tools: all %d assertions OK\n", 3);
    return 0;
}
