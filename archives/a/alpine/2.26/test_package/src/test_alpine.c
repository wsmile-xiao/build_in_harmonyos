#include <stdio.h>
#include <string.h>

int main(int argc, char **argv) {
    if (argc < 2) {
        fprintf(stderr, "usage: test_alpine <alpine-binary>\n");
        return 2;
    }
    char cmd[1024];
    snprintf(cmd, sizeof(cmd), "%s --version 2>&1", argv[1]);
    FILE *fp = popen(cmd, "r");
    if (!fp) {
        fprintf(stderr, "popen failed\n");
        return 1;
    }
    char buf[4096];
    size_t n = fread(buf, 1, sizeof(buf) - 1, fp);
    buf[n] = '\0';
    pclose(fp);
    /* 关键字检查：alpine --version 输出含 "Alpine"（版本信息）。
     * 不用 "alpine"（二进制名子串）——二进制未找到时 shell 错误消息
     * 含 "alpine" 会导致假阳性误报 PASS（drill 同类问题先例）。 */
    if (strstr(buf, "Alpine") != NULL) {
        printf("PASS: alpine --version 输出含 'Alpine'\n");
        return 0;
    }
    fprintf(stderr, "FAIL: alpine --version 输出缺 'Alpine'（输出: %s）\n", buf);
    return 1;
}
