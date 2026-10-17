#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <rpmalloc.h>

int main(void) {
    rpmalloc_initialize();
    void* p = rpmalloc(4096);
    if (!p) {
        fprintf(stderr, "rpmalloc allocation failed\n");
        rpmalloc_finalize();
        return 1;
    }
    memset(p, 0xAB, 4096);
    if (*(unsigned char*)p != 0xAB || ((unsigned char*)p)[4095] != 0xAB) {
        fprintf(stderr, "rpmalloc memory content mismatch\n");
        rpfree(p);
        rpmalloc_finalize();
        return 1;
    }
    void* q = rprealloc(p, 16384);
    if (!q) {
        fprintf(stderr, "rprealloc failed\n");
        rpmalloc_finalize();
        return 1;
    }
    if (((unsigned char*)q)[4095] != 0xAB) {
        fprintf(stderr, "rprealloc content mismatch\n");
        rpfree(q);
        rpmalloc_finalize();
        return 1;
    }
    rpfree(q);
    rpmalloc_finalize();
    printf("test rpmalloc 1.4.5: OK\n");
    return 0;
}
