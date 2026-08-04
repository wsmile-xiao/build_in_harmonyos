/**
 * test_pcalc.c — 验证 pcalc 工具是否可用。
 *
 * 通过 system() 调用 pcalc 二进制执行 1+1 计算，
 * 验证工具可正常运行并输出正确结果 "2"。
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/wait.h>
#include <unistd.h>

static int run_cmd(const char *cmd) {
    int ret = system(cmd);
    if (ret == -1) return -1;
    return WIFEXITED(ret) && WEXITSTATUS(ret) == 0 ? 0 : -1;
}

/* Check if a file contains a given substring. */
static int file_contains(const char *path, const char *needle) {
    FILE *f = fopen(path, "r");
    if (!f) return 0;
    char buf[256];
    while (fgets(buf, sizeof(buf), f)) {
        if (strstr(buf, needle)) {
            fclose(f);
            return 1;
        }
    }
    fclose(f);
    return 0;
}

int main(void) {
    int ret;

    /* Create a temporary file with a unique name in the current
     * (build) directory — /tmp is read-only on the CI filesystem,
     * and this avoids shell injection through TMPDIR by not reading
     * the environment at all. */
    char out_path[] = "pcalc_test_XXXXXX";
    int fd = mkstemp(out_path);
    if (fd == -1) {
        perror("mkstemp");
        return 1;
    }
    close(fd);

    /* Test: run pcalc 1+1 and verify it produces correct output */
    printf("Test: pcalc 1+1 ... ");
    char cmd[1024];
    snprintf(cmd, sizeof(cmd), "pcalc '1+1' > %s 2>&1", out_path);
    ret = run_cmd(cmd);
    if (ret != 0) {
        printf("FAIL (exit code)\n");
        remove(out_path);
        return 1;
    }
    if (!file_contains(out_path, "2")) {
        printf("FAIL (expected output to contain '2')\n");
        remove(out_path);
        return 1;
    }
    remove(out_path);
    printf("PASS\n");

    printf("All tests passed.\n");
    return 0;
}