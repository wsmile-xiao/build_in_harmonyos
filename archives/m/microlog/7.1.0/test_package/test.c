/*
 * test.c — Conan test_package consumer test for microlog 7.1.0
 *
 * Real consumer validation (R34): includes only the package's public
 * header <ulog.h>, emits a message through the public ulog_info() macro
 * (default stdout output), and verifies the observable formatted output
 * by capturing stdout into a file. This exercises the actual logging
 * pipeline with the packaged default configuration.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ulog.h>

int main(void) {
    const char *cap = "test_capture.log";
    FILE *out = freopen(cap, "w", stdout);
    if (out == NULL) {
        perror("freopen");
        return 1;
    }

    /* Emit through the public logging macro (default stdout output). */
    ulog_info("consumer hello from microlog");
    fflush(stdout);
    fclose(out);

    /* Read back the captured stdout and verify observable output. */
    FILE *in = fopen(cap, "r");
    if (in == NULL) {
        perror("fopen");
        return 1;
    }
    char buf[2048];
    size_t n = fread(buf, 1, sizeof(buf) - 1, in);
    fclose(in);
    buf[n] = '\0';

    if (strstr(buf, "consumer hello from microlog") == NULL) {
        fprintf(stderr, "FAIL: captured output missing message: '%s'\n", buf);
        return 1;
    }
    if (strstr(buf, "INFO") == NULL) {
        fprintf(stderr, "FAIL: level string missing in output: '%s'\n", buf);
        return 1;
    }

    printf("test_microlog: OK (captured %zu bytes: %s)", n, buf);
    return 0;
}