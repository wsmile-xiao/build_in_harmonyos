#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* Test figlet CLI tool by calling it via popen and verifying output.
 * R34: test must substantively depend on the tested package's binary. */
int main(void) {
    char cmd[256];
    char buf[4096];
    size_t n;

    /* Get font directory from environment or use default */
    const char *fontdir = getenv("FIGLET_FONTDIR");
    if (!fontdir) fontdir = "/usr/local/share/figlet";

    /* Get figlet binary path from environment */
    const char *figlet = getenv("FIGLET_BIN");
    if (!figlet) figlet = "figlet";

    /* Test 1: Check version infocode (should be 20205 for v2.2.5) */
    snprintf(cmd, sizeof(cmd), "%s -I 1 2>&1", figlet);
    FILE *fp = popen(cmd, "r");
    if (!fp) {
        fprintf(stderr, "FAIL: cannot run figlet\n");
        return 1;
    }
    n = fread(buf, 1, sizeof(buf) - 1, fp);
    buf[n] = '\0';
    pclose(fp);

    if (strstr(buf, "20205") == NULL) {
        fprintf(stderr, "FAIL: version infocode mismatch, got: %s\n", buf);
        return 1;
    }
    printf("PASS: version infocode = 20205\n");

    /* Test 2: Generate ASCII art and verify non-empty output */
    snprintf(cmd, sizeof(cmd), "%s -d %s Hello 2>&1", figlet, fontdir);
    fp = popen(cmd, "r");
    if (!fp) {
        fprintf(stderr, "FAIL: cannot run figlet for text output\n");
        return 1;
    }
    n = fread(buf, 1, sizeof(buf) - 1, fp);
    buf[n] = '\0';
    pclose(fp);

    if (n < 10) {
        fprintf(stderr, "FAIL: figlet output too short (%zu bytes)\n", n);
        return 1;
    }
    /* Check for character 'H' pattern in the output (ASCII art) */
    if (strchr(buf, '_') == NULL && strchr(buf, '|') == NULL) {
        fprintf(stderr, "FAIL: figlet output doesn't look like ASCII art\n");
        return 1;
    }
    printf("PASS: ASCII art output contains expected characters (%zu bytes)\n", n);

    printf("All figlet tests passed.\n");
    return 0;
}
