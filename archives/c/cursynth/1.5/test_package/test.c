/*
 * test.c — cursynth test_package consumer test.
 *
 * cursynth is a command-line tool, not a library, so this test runs the
 * packaged `cursynth` binary and asserts on its observable behaviour:
 *   1. `cursynth -V` prints the upstream version banner ("Cursynth 1.5").
 *   2. `cursynth -b 512` without an audio device still initialises the OSS
 *      back-end and reports "No audio devices found." with exit status 0.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int run(const char *cmd, char *out, size_t cap) {
    FILE *p = popen(cmd, "r");
    size_t n;
    if (!p)
        return -1;
    n = fread(out, 1, cap - 1, p);
    out[n] = '\0';
    return pclose(p);
}

int main(void) {
    char out[1024];
    int rc;

    rc = run("cursynth -V 2>&1", out, sizeof(out));
    if (rc != 0) {
        fprintf(stderr, "FAIL: cursynth -V exited with %d\n", rc);
        return 1;
    }
    if (strstr(out, "Cursynth 1.5") == NULL) {
        fprintf(stderr, "FAIL: unexpected version output: %s\n", out);
        return 1;
    }
    printf("PASS: version banner: %.40s", out);

    /* Without an audio device the tool must still start, initialise the OSS
       back-end and report that no device is available (exit status 0). */
    rc = run("cursynth -b 512 2>&1", out, sizeof(out));
    if (rc != 0) {
        fprintf(stderr, "FAIL: cursynth (no device) exited with %d\n", rc);
        return 1;
    }
    if (strstr(out, "No audio devices found") == NULL) {
        fprintf(stderr, "FAIL: expected no-device diagnostic, got: %s\n", out);
        return 1;
    }
    printf("PASS: no-audio-device path: %.60s", out);
    return 0;
}
