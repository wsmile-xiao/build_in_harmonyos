/* checkit-tiff test_package smoke test.
 *
 * checkit_tiff is a CLI conformance checker (application package, no public
 * headers), so the consumer test drives the installed binary instead of
 * linking a library. `checkit_tiff -h` prints usage and exits EXIT_SUCCESS
 * (see src/checkit_tiff.c upstream). Exit codes are propagated through
 * system() so a non-zero run fails the CTest test.
 */
#include <stdio.h>
#include <stdlib.h>

int main(void) {
    int rc = system("checkit_tiff -h > /dev/null 2>&1");
    if (rc != 0) {
        printf("checkit-tiff test FAILED: 'checkit_tiff -h' exited %d\n", rc);
        return 1;
    }
    printf("checkit-tiff 1.7.3: OK (help invocation exits 0)\n");
    return 0;
}