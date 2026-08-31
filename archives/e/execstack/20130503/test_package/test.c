/*
 * test_execstack.c — Test that execstack binary is functional
 *
 * This test invokes the execstack CLI tool with --version to verify
 * the binary was correctly built and can execute. execstack is a CLI
 * application (not a library), so we test by running the binary.
 *
 * The EXECSTACK_BIN environment variable is set by the test harness
 * (conanfile.py) to point to the installed execstack binary.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/wait.h>

int main(void) {
    /* Get execstack binary path from environment */
    const char *execstack_path = getenv("EXECSTACK_BIN");
    if (!execstack_path || strlen(execstack_path) == 0) {
        execstack_path = "execstack";
    }

    /* Build command: execstack --version */
    char cmd[512];
    snprintf(cmd, sizeof(cmd), "%s --version", execstack_path);

    /* Run execstack --version and capture output */
    FILE *fp = popen(cmd, "r");
    if (fp == NULL) {
        fprintf(stderr, "Failed to run execstack\n");
        return 1;
    }

    char buf[256];
    int found_version = 0;
    while (fgets(buf, sizeof(buf), fp) != NULL) {
        /* Check for expected version output containing "execstack" */
        if (strstr(buf, "execstack") != NULL) {
            found_version = 1;
            printf("execstack version output: %s", buf);
        }
    }
    int ret = pclose(fp);

    /* Primary criterion: execstack must exit successfully.
       Relying solely on output sniffing lets a failing/crashing binary
       that happens to print "execstack" to stderr slip through. */
    int exit_status = -1;
    if (ret != -1) {
        if (WIFEXITED(ret))
            exit_status = WEXITSTATUS(ret);
        else
            exit_status = 128 + WTERMSIG(ret); /* signal-terminated */
    }

    if (exit_status != 0) {
        fprintf(stderr, "execstack --version exited with status %d\n", exit_status);
        return 1;
    }

    if (!found_version) {
        fprintf(stderr, "execstack --version exited 0 but produced no expected output\n");
        return 1;
    }

    printf("test_execstack: PASSED\n");
    return 0;
}
