#include <stdio.h>
#include <jasper/jasper.h>
int main(void) {
    if (jas_init() != 0) { fprintf(stderr, "jas_init() failed\n"); return 1; }
    printf("JasPer version: %s\n", jas_getversion());
    int num_fmts = jas_image_getnumfmts();
    if (num_fmts <= 0) { fprintf(stderr, "No image formats\n"); jas_cleanup(); return 1; }
    printf("Number of image formats: %d\n", num_fmts);
    jas_cleanup();
    printf("test jasper 4.2.9: OK\n");
    return 0;
}
