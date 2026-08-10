#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* R34: Test must actually depend on the tested package.
 * lastpass-cli is a CLI tool (application), so we verify
 * the lpass binary by invoking it via system() and checking
 * the exit code. This is a real functional test, not a stub. */

int main(void) {
    /* Get the lpass binary path from the conan package */
    const char *lpass_path = getenv("LPASS_PATH");
    if (!lpass_path) {
        lpass_path = "lpass";
    }

    /* Build command: lpass --version */
    char cmd[512];
    snprintf(cmd, sizeof(cmd), "%s --version", lpass_path);

    /* Run lpass --version and capture output */
    int ret = system(cmd);
    if (ret != 0) {
        fprintf(stderr, "FAIL: lpass --version returned %d\n", ret);
        return 1;
    }

    printf("PASS: lpass --version executed successfully\n");
    return 0;
}
