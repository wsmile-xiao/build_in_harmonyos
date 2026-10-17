#include <MagickWand/MagickWand.h>
#include <stdio.h>

int main(void) {
    MagickWandGenesis();
    MagickWand *wand = NewMagickWand();
    if (wand == NULL) {
        fprintf(stderr, "Failed to create MagickWand\n");
        MagickWandTerminus();
        return 1;
    }
    MagickSetSize(wand, 1, 1);
    if (MagickReadImage(wand, "xc:red") != MagickTrue) {
        fprintf(stderr, "Failed to read image\n");
        DestroyMagickWand(wand);
        MagickWandTerminus();
        return 1;
    }
    const char *ver = MagickGetVersion(NULL);
    printf("ImageMagick version: %s\n", ver ? ver : "unknown");
    DestroyMagickWand(wand);
    MagickWandTerminus();
    return 0;
}
