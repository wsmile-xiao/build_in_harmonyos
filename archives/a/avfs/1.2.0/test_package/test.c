#include <stdio.h>

/* Verify that avfs headers are accessible via Conan package */
#include <avfs.h>

int main(void) {
    printf("avfs 1.2.0 test: OK (headers found, package linked)\n");
    return 0;
}
