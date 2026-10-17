/* test_package.c — texlive test
 * Calls tex/pdftex binaries to verify installation.
 * This test verifies that the texlive package provides working binaries.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(int argc, char *argv[]) {
    /* Check that we can find the tex binary via PATH */
    int ret = system("tex --version > /dev/null 2>&1");
    if (ret != 0) {
        fprintf(stderr, "ERROR: tex --version failed\n");
        return 1;
    }
    /* Check pdftex */
    ret = system("pdftex --version > /dev/null 2>&1");
    if (ret != 0) {
        fprintf(stderr, "ERROR: pdftex --version failed\n");
        return 1;
    }
    printf("texlive test: tex and pdftex binaries are functional\n");
    return 0;
}
