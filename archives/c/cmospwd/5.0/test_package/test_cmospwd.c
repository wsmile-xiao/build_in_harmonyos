/* test_cmospwd.c: consumer test for cmospwd 5.0 (R34 substantive, no shell-out stub).
 * Test 1: usage output via unknown option (no hardware access, no stdin block).
 * Test 2: file-backed decode via "-l backup -m1" (single module, no wait_key).
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int run_capture(const char *cmd, char *out, size_t cap) {
    FILE *p = popen(cmd, "r");
    if (!p) return -1;
    size_t n = 0;
    int c;
    while ((c = fgetc(p)) != EOF && n + 1 < cap) {
        out[n++] = (char)c;
    }
    out[n] = '\0';
    return pclose(p);
}

static int test_usage(const char *bin) {
    char cmd[4096];
    char out[8192];
    snprintf(cmd, sizeof(cmd), "\"%s\" --help 2>&1", bin);
    int rc = run_capture(cmd, out, sizeof(out));
    if (rc != 0) {
        printf("[FAIL] usage: exit=%d\n", rc);
        return 1;
    }
    if (strstr(out, "Usage") == NULL && strstr(out, "CmosPwd") == NULL) {
        printf("[FAIL] usage: missing Usage/CmosPwd marker\n%s\n", out);
        return 1;
    }
    printf("[PASS] usage output contains help marker\n");
    return 0;
}

static int test_file_decode(const char *bin) {
    const char *tmp = "cmospwd_test_backup.bin";
    FILE *f = fopen(tmp, "wb");
    if (!f) {
        printf("[FAIL] decode: cannot create backup file\n");
        return 1;
    }
    unsigned char zeros[128];
    memset(zeros, 0, sizeof(zeros));
    if (fwrite(zeros, 1, sizeof(zeros), f) != sizeof(zeros)) {
        fclose(f);
        printf("[FAIL] decode: cannot write backup file\n");
        return 1;
    }
    fclose(f);
    char cmd[4096];
    char out[16384];
    snprintf(cmd, sizeof(cmd), "\"%s\" -l %s -m1 2>&1", bin, tmp);
    int rc = run_capture(cmd, out, sizeof(out));
    remove(tmp);
    if (rc != 0) {
        printf("[FAIL] decode: exit=%d\n%s\n", rc, out);
        return 1;
    }
    if (strstr(out, "CmosPwd") == NULL) {
        printf("[FAIL] decode: missing CmosPwd banner\n%s\n", out);
        return 1;
    }
    printf("[PASS] file-backed decode runs one module successfully\n");
    return 0;
}

int main(int argc, char *argv[]) {
    if (argc < 2) {
        printf("usage: test_cmospwd <cmospwd-binary>\n");
        return 1;
    }
    int fails = 0;
    fails += test_usage(argv[1]);
    fails += test_file_decode(argv[1]);
    if (fails == 0) {
        printf("ALL TESTS PASSED (2/2)\n");
        return 0;
    }
    printf("TESTS FAILED: %d\n", fails);
    return 1;
}
