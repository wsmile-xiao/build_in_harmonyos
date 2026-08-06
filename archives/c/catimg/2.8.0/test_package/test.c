#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(void) {
    /* R34: Test that catimg binary is installed and functional.
     * catimg -h returns exit code 1 but outputs usage text,
     * so we check the output content rather than exit code. */
    FILE *fp = popen("catimg -h 2>&1", "r");
    if (fp == NULL) {
        printf("FAIL: Cannot execute catimg\n");
        return 1;
    }
    char buf[256];
    int found = 0;
    while (fgets(buf, sizeof(buf), fp) != NULL) {
        if (strstr(buf, "Usage") != NULL) {
            found = 1;
        }
    }
    pclose(fp);
    if (!found) {
        printf("FAIL: catimg did not output Usage\n");
        return 1;
    }
    printf("PASS: catimg binary is functional\n");
    return 0;
}
