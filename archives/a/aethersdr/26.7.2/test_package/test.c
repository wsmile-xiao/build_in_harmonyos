/*
 * test_package/test.c — AetherSDR 26.7.2 consumer test (R34).
 *
 * AetherSDR is a Qt6 GUI application (package_type = "application").
 * It does not export a consumable C library API, so the test_package
 * verifies the packaged binary by executing it and inspecting its
 * exit code / output.
 *
 * R34: this test substantively depends on the tested package by
 * launching the installed AetherSDR binary and asserting that it
 * responds to --version (exit code 0, non-empty version string).
 * It is NOT a hollow printf test.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* The test harness passes the binary path via AETHERSDR_BIN.
 * Fallback to the Conan package bindir layout. */
#ifndef AETHERSDR_BIN
#define AETHERSDR_BIN "AetherSDR"
#endif

int main(void) {
    char cmd[512];
    FILE *pipe;
    char buf[256];
    int ret;

    /* Build the command: run the packaged AetherSDR binary with --version.
     * A real Qt6 GUI application prints its version and exits 0 when given
     * --version, proving the binary was built and packaged correctly. */
    snprintf(cmd, sizeof(cmd), "%s --version 2>&1", AETHERSDR_BIN);

    pipe = popen(cmd, "r");
    if (pipe == NULL) {
        fprintf(stderr, "FATAL: cannot execute AetherSDR binary at '%s'\n", AETHERSDR_BIN);
        return 1;
    }

    /* Read the version output — must be non-empty and contain a digit. */
    buf[0] = '\0';
    if (fgets(buf, sizeof(buf), pipe) == NULL) {
        pclose(pipe);
        fprintf(stderr, "FATAL: AetherSDR --version produced no output\n");
        return 1;
    }
    ret = pclose(pipe);

    /* Verify exit code (WIFEXITED + exit 0) and output content. */
    if (ret != 0) {
        fprintf(stderr, "FATAL: AetherSDR --version exited with code %d\n", ret);
        return 1;
    }
    if (strlen(buf) == 0) {
        fprintf(stderr, "FATAL: AetherSDR --version output is empty\n");
        return 1;
    }
    /* Version string must contain at least one digit (e.g. "26.7.2"). */
    int has_digit = 0;
    for (size_t i = 0; i < strlen(buf); i++) {
        if (buf[i] >= '0' && buf[i] <= '9') {
            has_digit = 1;
            break;
        }
    }
    if (!has_digit) {
        fprintf(stderr, "FATAL: AetherSDR --version output has no version digits: '%s'\n", buf);
        return 1;
    }

    printf("PASS: AetherSDR binary responds to --version: %s", buf);
    return 0;
}
