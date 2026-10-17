#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(int argc, char *argv[]) {
    int passed = 0, failed = 0;
    const char *hping3 = (argc > 1) ? argv[1] : "hping3";
    char cmd[512];
    snprintf(cmd, sizeof(cmd), "%s --version > /dev/null 2>&1", hping3);
    int ret = system(cmd);
    if (ret == 0) passed++; else failed++;
    snprintf(cmd, sizeof(cmd), "%s --help > /dev/null 2>&1", hping3);
    ret = system(cmd);
    if (ret == 0) passed++; else failed++;
    snprintf(cmd, sizeof(cmd), "%s --version 2>&1", hping3);
    FILE *fp = popen(cmd, "r");
    if (fp) {
        char buf[256] = {0};
        if (fgets(buf, sizeof(buf), fp) && strstr(buf, "hping")) passed++;
        else failed++;
        pclose(fp);
    } else failed++;
    printf("Tests: %d passed, %d failed\n", passed, failed);
    return failed > 0 ? 1 : 0;
}
