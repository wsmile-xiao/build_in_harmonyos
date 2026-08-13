#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(void) {
    FILE *fp = popen("ipinfo 192.168.1.0/24", "r");
    if (fp == NULL) {
        fprintf(stderr, "Failed to run ipinfo\n");
        return 1;
    }
    char buf[256];
    if (fgets(buf, sizeof(buf), fp) == NULL) {
        pclose(fp);
        fprintf(stderr, "ipinfo produced no output\n");
        return 1;
    }
    pclose(fp);
    if (strstr(buf, "192") != NULL) {
        printf("PASS: ipinfo binary works correctly\n");
        return 0;
    }
    fprintf(stderr, "FAIL: unexpected output: %s", buf);
    return 1;
}
