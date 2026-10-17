#include <xmi.h>
#include <stdio.h>

/* Coordinate mode enum value (X11-style CoordModeOrigin, see extern.h). */
#define COORD_MODE_ORIGIN 0

int main(void)
{
    miPixel pixels[2] = { 0, 1 };            /* background, foreground */
    miPoint pts[3] = { {0, 0}, {50, 50}, {63, 0} };
    miPoint origin = { 0, 0 };

    miGC *gc = miNewGC(2, pixels);
    miPaintedSet *ps = miNewPaintedSet();
    miCanvas *canvas = miNewCanvas(64, 64, pixels[0]);
    if (!gc || !ps || !canvas) {
        fprintf(stderr, "libxmi: object creation failed\n");
        return 1;
    }

    /* Rasterize a polyline through the full public pipeline:
       GC -> painted set (spans) -> canvas. */
    miDrawLines(ps, gc, COORD_MODE_ORIGIN, 3, pts);
    miCopyPaintedSetToCanvas(ps, canvas, origin);

    miDeleteCanvas(canvas);
    miDeletePaintedSet(ps);
    miDeleteGC(gc);

    printf("libxmi draw pipeline OK\n");
    return 0;
}
