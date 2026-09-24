#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* R34: Test must actually exercise the installed binary.
 * Run `pure-ftpd --help` via popen and verify it produces output
 * containing known option flags. */
int main(void) {
    FILE *fp;
    char buf[256];
    int found_option = 0;

    fp = popen("pure-ftpd --help 2>&1", "r");
    if (fp == NULL) {
        fprintf(stderr, "FAIL: cannot execute pure-ftpd\n");
        return 1;
    }

    while (fgets(buf, sizeof(buf), fp) != NULL) {
        if (strstr(buf, "--") != NULL) {
            found_option = 1;
            break;
        }
    }

    pclose(fp);

    if (!found_option) {
        fprintf(stderr, "FAIL: pure-ftpd --help did not produce expected output\n");
        return 1;
    }

    printf("pure-ftpd --help: PASS (binary executes and shows options)\n");
    return 0;
}
