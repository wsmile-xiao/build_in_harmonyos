/* 消费者测试：运行被测引擎二进制并断言真实行为（R34）。
 * 1) --version：退出码 0，输出包含 "version"；
 * 2) 引擎对局回路：stdin 喂 "quit"，断言输出含 "GNU Shogi" 横幅
 *    且进程干净退出（exit code 0）。
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int fail(const char *msg) {
    fprintf(stderr, "gnushogi consumer FAIL: %s\n", msg);
    return 1;
}

int main(void) {
    const char *engine = getenv("GNUSHOGI_BIN");
    if (engine == NULL || engine[0] == '\0') {
        return fail("GNUSHOGI_BIN not set");
    }

    char cmd[4600];
    char buf[512];
    int rc;

    /* 1) --version 必须干净退出并报出版本 */
    snprintf(cmd, sizeof(cmd), "\"%s\" --version 2>&1", engine);
    FILE *p = popen(cmd, "r");
    if (p == NULL) {
        return fail("popen(--version) failed");
    }
    buf[0] = '\0';
    if (fgets(buf, sizeof(buf), p) == NULL) {
        pclose(p);
        return fail("--version produced no output");
    }
    rc = pclose(p);
    if (rc != 0) {
        return fail("--version exited nonzero");
    }
    if (strstr(buf, "version") == NULL) {
        return fail("--version output lacks version string");
    }

    /* 2) 引擎主回路：读入 quit 命令前打印横幅，之后退出码 0 */
    snprintf(cmd, sizeof(cmd), "echo quit | \"%s\" 2>&1", engine);
    p = popen(cmd, "r");
    if (p == NULL) {
        return fail("popen(engine) failed");
    }
    int found_banner = 0;
    while (fgets(buf, sizeof(buf), p) != NULL) {
        if (strstr(buf, "GNU Shogi") != NULL) {
            found_banner = 1;
        }
    }
    rc = pclose(p);
    if (!found_banner) {
        return fail("engine banner missing");
    }
    if (rc != 0) {
        return fail("engine exited nonzero after quit");
    }

    printf("gnushogi consumer: OK\n");
    return 0;
}
