/*
 * Consumer test for pnscan 1.14.1.
 *
 * Drives the packaged binaries as a library/tool consumer would:
 *   1. start t_listen (upstream echo test daemon; prints its port);
 *   2. run "pnscan -r \"Hello\" 127.0.0.1 <port>";
 *   3. assert pnscan exits 0 and reports the "Hello, World!" banner.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(void) {
    const char *bindir = getenv("PNSCAN_BIN");
    if (!bindir || bindir[0] == '\0') {
        fprintf(stderr, "FAIL: PNSCAN_BIN not set\n");
        return 1;
    }

    char cmd[1024];
    snprintf(cmd, sizeof cmd, "\"%s/t_listen\"", bindir);
    FILE *fp = popen(cmd, "r");
    if (!fp) {
        perror("FAIL: popen(t_listen)");
        return 2;
    }
    int port = 0;
    if (fscanf(fp, "%d", &port) != 1 || port <= 0 || port > 65535) {
        fprintf(stderr, "FAIL: cannot parse port from t_listen output\n");
        pclose(fp);
        return 3;
    }
    pclose(fp);

    snprintf(cmd, sizeof cmd, "\"%s/pnscan\" -r \"Hello\" 127.0.0.1 %d 2>&1",
             bindir, port);
    fp = popen(cmd, "r");
    if (!fp) {
        perror("FAIL: popen(pnscan)");
        return 4;
    }
    char buf[8192];
    memset(buf, 0, sizeof buf);
    size_t n = fread(buf, 1, sizeof buf - 1, fp);
    (void)n;
    int rc = pclose(fp);
    if (rc != 0) {
        fprintf(stderr, "FAIL: pnscan exited %d\noutput:\n%s\n", rc, buf);
        return 5;
    }
    if (!strstr(buf, "Hello, World!")) {
        fprintf(stderr,
                "FAIL: scan report missing 'Hello, World!' banner\noutput:\n%s\n",
                buf);
        return 6;
    }

    printf("dd_consumer OK: pnscan scanned 127.0.0.1:%d, banner matched\n",
           port);
    return 0;
}
