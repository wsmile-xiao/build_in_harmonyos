#include <stdio.h>
#include <stdlib.h>

/* Minimal test source for CI L0e gate.
 * The actual test runs ndisc6 --version via conanfile.py test(). */
int main(void) {
    printf("ndisc6 test package: build OK\n");
    return 0;
}
