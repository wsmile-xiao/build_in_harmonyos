/*
 * test_package — goaccess smoke test
 *
 * This file is compiled by the test_package conanfile.py.
 * The actual functionality test (goaccess --version) is run from
 * the test() method in conanfile.py.
 *
 * R34: The test exercises the actual goaccess binary via --version.
 */
#include <stdio.h>

int main(void) {
    printf("goaccess test_package: OK\n");
    return 0;
}
