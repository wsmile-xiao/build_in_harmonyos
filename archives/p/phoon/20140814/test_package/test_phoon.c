/* test_phoon.c — verifies phoon binary runs and produces output.
 *
 * This test calls the phoon binary installed by the phoon/20140814 package
 * and checks that it produces non-empty output (a moon phase ASCII art).
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(void) {
    char cmd[256];
    /* Use the phoon binary from PATH (set by Conan VirtualRunEnv) */
    snprintf(cmd, sizeof(cmd), "phoon -l 20");
    FILE *fp = popen(cmd, "r");
    if (!fp) {
        fprintf(stderr, "FAIL: cannot run phoon\n");
        return 1;
    }

    char buf[4096];
    size_t total = 0;
    size_t n;
    while ((n = fread(buf + total, 1, sizeof(buf) - total - 1, fp)) > 0) {
        total += n;
        if (total >= sizeof(buf) - 1)
            break;
    }
    int status = pclose(fp);

    buf[total] = '\0';

    /* phoon output should contain "Moon" (e.g., "New Moon", "Full Moon") */
    if (strstr(buf, "Moon") == NULL) {
        fprintf(stderr, "FAIL: phoon output does not contain 'Moon'\n");
        fprintf(stderr, "Output: %s\n", buf);
        return 1;
    }

    /* Check exit status: non-zero means phoon crashed or errored (R34) */
    if (status != 0) {
        fprintf(stderr, "FAIL: phoon exited with non-zero status %d\n", status);
        return 1;
    }

    printf("PASS: phoon produced %zu bytes with moon phase info\n", total);
    return 0;
}
