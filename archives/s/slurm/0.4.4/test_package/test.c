#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/wait.h>

int main(int argc, char *argv[]) {
    const char *slurm_bin = (argc > 1) ? argv[1] : "slurm";
    char cmd[512];
    FILE *fp;
    char buf[256];
    int saw_usage = 0;
    int ret;

    printf("Testing slurm binary: %s\n", slurm_bin);

    /* Check 1: `slurm -h` exits 0 (upstream slurm.c: usage(0, argv)) */
    snprintf(cmd, sizeof(cmd), "\"%s\" -h 2>&1", slurm_bin);
    ret = system(cmd);
    if (ret == -1) {
        perror("system");
        return 1;
    }
    if (!WIFEXITED(ret) || WEXITSTATUS(ret) != 0) {
        fprintf(stderr, "FAIL: slurm -h returned %d\n", ret);
        return 1;
    }
    printf("PASS: slurm -h exit code 0\n");

    /* Check 2: usage banner contains the canonical usage line */
    fp = popen(cmd, "r");
    if (fp == NULL) {
        perror("popen");
        return 1;
    }
    while (fgets(buf, sizeof(buf), fp) != NULL) {
        if (strstr(buf, "usage:") != NULL) {
            saw_usage = 1;
            break;
        }
    }
    ret = pclose(fp);
    if (!WIFEXITED(ret) || WEXITSTATUS(ret) != 0) {
        fprintf(stderr, "FAIL: slurm -h second run returned %d\n", ret);
        return 1;
    }
    if (!saw_usage) {
        fprintf(stderr, "FAIL: slurm -h output missing 'usage:' line\n");
        return 1;
    }
    printf("PASS: slurm -h usage banner OK\n");

    printf("All tests passed\n");
    return 0;
}
