#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(void) {
    /* R34: Execute stuntman binary to verify package is correctly built */
    FILE *fp = popen("stunclient --help 2>&1", "r");
    if (fp == NULL) {
        fprintf(stderr, "stuntman: failed to run stunclient\n");
        return 1;
    }
    char buf[256];
    int found = 0;
    while (fgets(buf, sizeof(buf), fp) != NULL) {
        if (strstr(buf, "STUNCLIENT") != NULL) {
            found = 1;
            break;
        }
    }
    pclose(fp);
    if (!found) {
        fprintf(stderr, "stuntman: stunclient output unexpected\n");
        return 1;
    }
    printf("stuntman 1.2.16: stunclient OK\n");
    return 0;
}
