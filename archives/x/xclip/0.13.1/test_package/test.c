#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* R34: 实质依赖被测包 —— 执行 xclip 二进制并校验版本输出 */
int main(void) {
    char buf[512] = {0};
    FILE *fp = popen("xclip -version 2>&1", "r");
    if (!fp) {
        fprintf(stderr, "FAIL: cannot run xclip -version\n");
        return 1;
    }
    size_t n = fread(buf, 1, sizeof(buf) - 1, fp);
    buf[n] = '\0';
    int rc = pclose(fp);
    if (rc != 0) {
        fprintf(stderr, "FAIL: xclip -version exit=%d\n", rc);
        return 1;
    }
    if (strstr(buf, "xclip version") == NULL) {
        fprintf(stderr, "FAIL: unexpected xclip output: %s\n", buf);
        return 1;
    }
    printf("PASS: %s", buf);
    return 0;
}
