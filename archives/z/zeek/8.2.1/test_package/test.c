#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(void) {
    const char* cmd = "zeek --version";
    FILE* fp = popen(cmd, "r");
    if ( ! fp ) {
        fprintf(stderr, "FAIL: popen(%s) failed\n", cmd);
        return 1;
    }

    char buf[256] = {0};
    if ( ! fgets(buf, sizeof(buf), fp) ) {
        fprintf(stderr, "FAIL: no output from zeek --version\n");
        pclose(fp);
        return 1;
    }

    int rc = pclose(fp);
    if ( rc != 0 ) {
        fprintf(stderr, "FAIL: zeek --version exited rc=%d\n", rc);
        return 1;
    }

    // zeek --version prints e.g. "zeek version 8.2.1"
    if ( strstr(buf, "zeek version 8.2.1") == NULL ) {
        fprintf(stderr, "FAIL: unexpected zeek --version output: %s\n", buf);
        return 1;
    }

    printf("test zeek 8.2.1: OK (ran zeek --version) : %s", buf);
    return 0;
}
