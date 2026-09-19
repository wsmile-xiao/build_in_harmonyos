#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* R34: test_package must substantively exercise the tested package.
 * das-watchdog is a CLI watchdog tool; the real consumer contract is its
 * command-line interface. Run `das_watchdog --version` and require it to
 * exit 0 and print a version banner (VERSION=0.9.0 baked at build time). */
int main(int argc, char **argv) {
    char cmd[512];
    char buf[512];
    FILE *fp;
    int exit_code;

    /* Locate the installed binary (test_package runs with conanrun env). */
    const char *bin = getenv("DAS_WATCHDOG_BIN");
    if (bin == NULL || *bin == '\0')
        bin = "das_watchdog";

    snprintf(cmd, sizeof(cmd), "%s --version", bin);
    fp = popen(cmd, "r");
    if (fp == NULL) {
        fprintf(stderr, "FAIL: cannot popen %s\n", cmd);
        return 1;
    }
    if (fgets(buf, sizeof(buf), fp) == NULL) {
        fprintf(stderr, "FAIL: no output from %s\n", cmd);
        pclose(fp);
        return 1;
    }
    exit_code = pclose(fp);

    printf("das-watchdog --version output: %s", buf);
    printf("pclose exit code: %d\n", exit_code);

    if (exit_code != 0) {
        fprintf(stderr, "FAIL: %s exited with %d\n", cmd, exit_code);
        return 1;
    }
    /* The version banner embeds VERSION=0.9.0 (Makefile -DVERSION). */
    if (strstr(buf, "0.9.0") == NULL) {
        fprintf(stderr, "FAIL: version banner does not contain 0.9.0\n");
        return 1;
    }
    printf("PASS: das-watchdog 0.9.0 CLI consumer test\n");
    return 0;
}
