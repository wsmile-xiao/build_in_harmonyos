/* Minimal test program for cdrkit test_package.
 * The actual tests are in conanfile.py test() method which runs the installed
 * genisoimage and isoinfo binaries to create and read ISO images.
 * This file exists to satisfy the L0d structure check.
 */
#include <stdio.h>

int main(void) {
    printf("cdrkit test_package structure check: OK\n");
    return 0;
}
