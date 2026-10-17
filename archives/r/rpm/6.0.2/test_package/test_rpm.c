/* test_rpm.c - Consumer test: link against librpm and call rpmReadConfigFiles */
#include <rpm/rpmlib.h>
#include <stdio.h>

int main(void) {
    /* Verify the library is linkable and the API is callable */
    int rc = rpmReadConfigFiles(NULL, NULL);
    if (rc != 0) {
        fprintf(stderr, "rpmReadConfigFiles failed: %d\n", rc);
        return 1;
    }
    /* Print version constant to verify linkage */
    printf("rpm version: %s\n", RPMVERSION);
    return 0;
}
