#include <libtwin/twin.h>

int main(void)
{
    twin_pixmap_t *pixmap = twin_pixmap_create(TWIN_ARGB32, 4, 3);
    if (pixmap == 0) return 1;
    if (pixmap->width != 4 || pixmap->height != 3) return 2;

    twin_fill(pixmap, 0xff123456u, TWIN_SOURCE, 0, 0, 4, 3);
    const twin_pointer_t pixel = twin_pixmap_pointer(pixmap, 2, 1);
    if (*pixel.argb32 != 0xff123456u) return 3;

    twin_pixmap_destroy(pixmap);
    return 0;
}
