#include <stdio.h>
#include <stdlib.h>

/* Include colord headers */
#include <colord.h>

int main(void) {
    /* Test basic colord API: create a color */
    CdColorRGB *rgb = cd_color_rgb_new();
    if (rgb == NULL) {
        fprintf(stderr, "Failed to create CdColorRGB\n");
        return 1;
    }

    /* Set and verify color values */
    cd_color_rgb_set(rgb, 0.5, 0.25, 0.75);
    if (rgb->R != 0.5 || rgb->G != 0.25 || rgb->B != 0.75) {
        fprintf(stderr, "Color values mismatch\n");
        cd_color_rgb_free(rgb);
        return 1;
    }

    printf("colord test_package: CdColorRGB API working correctly\n");
    printf("  RGB(%.2f, %.2f, %.2f) verified\n", rgb->R, rgb->G, rgb->B);

    /* Free the color (CdColorRGB is a simple struct, not GObject) */
    cd_color_rgb_free(rgb);

    return 0;
}
