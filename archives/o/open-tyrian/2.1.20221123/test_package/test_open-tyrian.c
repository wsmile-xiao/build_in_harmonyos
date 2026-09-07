#include <stdlib.h>
#include <stdio.h>
int main(void) {
    int rc = system("opentyrian --help > /dev/null 2>&1");
    if (rc != 0) { fprintf(stderr, "FAIL: opentyrian exited %d\n", rc); return 1; }
    printf("PASS: opentyrian binary runs correctly\n");
    return 0;
}
