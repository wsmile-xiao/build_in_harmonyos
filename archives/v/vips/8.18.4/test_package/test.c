#include <math.h>
#include <stdio.h>

#include <vips/vips.h>

int main(int argc, char **argv) {
    if (VIPS_INIT(argv[0])) {
        vips_error_exit(NULL);
    }

    VipsImage *image = vips_image_new_matrixv(2, 2, 1.0, 2.0, 3.0, 4.0);
    if (!image) {
        vips_shutdown();
        return 1;
    }

    double average = 0.0;
    if (vips_avg(image, &average, NULL)) {
        g_object_unref(image);
        vips_shutdown();
        return 1;
    }

    g_object_unref(image);
    vips_shutdown();

    if (fabs(average - 2.5) > 0.000001) {
        fprintf(stderr, "unexpected average: %.12f\n", average);
        return 1;
    }

    return 0;
}
