#include <stdio.h>

/*
 * sqsh is an interactive SQL shell shipped as a standalone application;
 * the real consumer validation runs in test_package/conanfile.py test()
 * (ELF arm64 check + `sqsh --help` usage output). This stub only exists
 * to satisfy the test_package build structure (L0m).
 */
int main(void)
{
    printf("sqsh test_package stub\n");
    return 0;
}
