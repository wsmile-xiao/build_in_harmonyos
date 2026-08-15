#include <stdio.h>
#include <string.h>

#include <gd.h>

static int check(int condition, const char *message)
{
    if (!condition) {
        fprintf(stderr, "FAIL: %s\n", message);
        return 1;
    }
    return 0;
}

int main(void)
{
    int failures = 0;

    const char *version = gdVersionString();
    failures += check(version != NULL && strstr(version, "2.3.3") != NULL,
                      "gdVersionString reports 2.3.3");

    gdImagePtr image = gdImageCreateTrueColor(16, 12);
    failures += check(image != NULL, "gdImageCreateTrueColor creates an image");
    if (image == NULL) {
        return 1;
    }

    failures += check(gdImageSX(image) == 16, "image width is 16");
    failures += check(gdImageSY(image) == 12, "image height is 12");

    int red = gdImageColorAllocate(image, 255, 0, 0);
    failures += check(red >= 0, "red color allocation succeeds");

    gdImageFilledRectangle(image, 2, 3, 7, 8, red);
    int pixel = gdImageGetPixel(image, 4, 4);
    failures += check(gdImageRed(image, pixel) == 255, "filled pixel red channel");
    failures += check(gdImageGreen(image, pixel) == 0, "filled pixel green channel");
    failures += check(gdImageBlue(image, pixel) == 0, "filled pixel blue channel");

    gdImageDestroy(image);

    if (failures != 0) {
        return 1;
    }

    printf("gd consumer checks passed\n");
    return 0;
}
