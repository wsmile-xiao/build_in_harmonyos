/*
 * test_easyrpg-player.c — L1 test for easyrpg-player conan package.
 *
 * This test verifies that the easyrpg-player binary is installed and
 * functional by executing it with --version and checking the output.
 * Satisfies R34: test depends on the package by executing its binary.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(void) {
    int rc;
    FILE *fp;
    char buf[256];

    /* Run easyrpg-player --version and capture output */
    fp = popen("easyrpg-player --version 2>&1", "r");
    if (fp == NULL) {
        fprintf(stderr, "Failed to run easyrpg-player\n");
        return 1;
    }

    if (fgets(buf, sizeof(buf), fp) != NULL) {
        /* Check that output contains "EasyRPG Player" */
        if (strstr(buf, "EasyRPG Player") != NULL) {
            printf("PASS: easyrpg-player --version: %s", buf);
            rc = 0;
        } else {
            printf("FAIL: unexpected output: %s", buf);
            rc = 1;
        }
    } else {
        printf("FAIL: no output from easyrpg-player --version\n");
        rc = 1;
    }

    pclose(fp);
    return rc;
}
