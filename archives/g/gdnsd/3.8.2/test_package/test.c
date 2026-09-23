#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(void) {
    /* R34: test must actually exercise the packaged binary.
     * gdnsd is a DNS server application; we verify it runs and reports
     * the correct version by calling the binary directly via popen. */
    FILE *fp = popen("gdnsd --version 2>&1", "r");
    if (fp == NULL) {
        fprintf(stderr, "Failed to run gdnsd --version\n");
        return 1;
    }

    char buf[256];
    int found = 0;
    while (fgets(buf, sizeof(buf), fp) != NULL) {
        if (strstr(buf, "3.8.2") != NULL) {
            found = 1;
            break;
        }
    }
    pclose(fp);

    if (found) {
        printf("gdnsd version 3.8.2 verified: OK\n");
        return 0;
    }
    fprintf(stderr, "gdnsd --version check failed\n");
    return 1;
}
