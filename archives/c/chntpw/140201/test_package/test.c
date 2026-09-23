// 消费者测试：真实运行 chntpw 包交付的 CLI 工具并断言行为。
// 断言点源自上游源码：chntpw.c:1047 "-h" → usage() → exit(0)；
// chntpw.c:1056 无参 → usage() → exit(1)；reged.c:105 "-h" → usage() → exit(0)。
// usage() 全部 printf 到 stdout（chntpw.c:997、reged.c:53）。
#include <stdio.h>
#include <stdlib.h>

static int run_cmd(const char *cmd) {
    int rc = system(cmd);
    if (rc < 0) {
        return -1;
    }
    return WEXITSTATUS(rc);
}

static int file_contains(const char *path, const char *needle) {
    FILE *f = fopen(path, "r");
    if (!f) {
        return 0;
    }
    char buf[512];
    int found = 0;
    while (fgets(buf, sizeof(buf), f)) {
        if (strstr(buf, needle)) {
            found = 1;
            break;
        }
    }
    fclose(f);
    return found;
}

int main(void) {
    const char *out = "chntpw-consumer-out.txt";

    // 1. chntpw -h：usage 正路径，退出码 0，stdout 含特征串
    int rc = run_cmd("chntpw -h > chntpw-consumer-out.txt 2>&1");
    if (rc != 0 || !file_contains(out, "change password of a user in a Windows SAM")) {
        fprintf(stderr, "FAIL: chntpw -h (rc=%d)\n", rc);
        return 1;
    }

    // 2. reged -h：usage 正路径，退出码 0，stdout 含 "Modes:"
    rc = run_cmd("reged -h > reged-consumer-out.txt 2>&1");
    if (rc != 0 || !file_contains("reged-consumer-out.txt", "Modes:")) {
        fprintf(stderr, "FAIL: reged -h (rc=%d)\n", rc);
        return 1;
    }

    // 3. chntpw 无参：usage + 退出码 1（chntpw.c:1056）
    rc = run_cmd("chntpw > chntpw-noarg.txt 2>&1");
    if (rc != 1) {
        fprintf(stderr, "FAIL: chntpw no-arg expected exit 1, got %d\n", rc);
        return 1;
    }

    // 4. sampasswd -h：usage 正路径（sampasswd.c 同构）
    rc = run_cmd("sampasswd -h > sampasswd-out.txt 2>&1");
    if (rc != 0) {
        fprintf(stderr, "FAIL: sampasswd -h (rc=%d)\n", rc);
        return 1;
    }

    printf("chntpw consumer test OK: chntpw/reged/sampasswd usage paths "
           "all behaved as upstream source declares\n");
    return 0;
}
