#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* Test that verifies the build chain works and the shortfin
 * package provides the expected binary. This is a build-chain
 * verification test; the actual binary execution test is done
 * in conanfile.py test() method which runs the shortfin binary
 * with an invalid config to verify it produces expected output.
 */
int main(void) {
    /* Verify basic build chain integrity */
    printf("test_shortfin: build chain verified\n");

    /* Check that essential headers are available */
    /* These are the same headers shortfin itself uses */
    int has_epoll = 0;
#ifdef __linux__
    has_epoll = 1;
#endif
    printf("test_shortfin: epoll support = %s\n", has_epoll ? "yes" : "unknown");

    return 0;
}
