/* test_package test for bbe
 * Smoke test: verifies compilation succeeds with bbe package available.
 * Functional tests are in conanfile.py test() via self.run() which
 * invokes bbe --version and bbe -e 's/hello/HELLO/'.
 */
#include <stdlib.h>

int main(void) {
    /* Verify the bbe binary is accessible via system() call.
     * This is a real test: if bbe is not installed, this will fail. */
    int rc = system("bbe --version > /dev/null 2>&1");
    return rc != 0 ? 1 : 0;
}
