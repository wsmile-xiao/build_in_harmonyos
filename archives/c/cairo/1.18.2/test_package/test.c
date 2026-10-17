#include <cairo.h>
#include <stdint.h>
#include <stdio.h>

int main(void)
{
    cairo_surface_t *surface = cairo_image_surface_create(CAIRO_FORMAT_ARGB32, 8, 8);
    cairo_t *cr = cairo_create(surface);
    cairo_set_source_rgba(cr, 1.0, 0.0, 0.0, 1.0);
    cairo_paint(cr);
    cairo_destroy(cr);
    cairo_surface_flush(surface);

    cairo_status_t status = cairo_surface_status(surface);
    if (status != CAIRO_STATUS_SUCCESS) {
        fprintf(stderr, "surface failed: %s\n", cairo_status_to_string(status));
        cairo_surface_destroy(surface);
        return 1;
    }
    uint32_t pixel = *(uint32_t *)cairo_image_surface_get_data(surface);
    cairo_surface_destroy(surface);
    if (pixel != UINT32_C(0xffff0000)) {
        fprintf(stderr, "unexpected rendered pixel: 0x%08x\n", pixel);
        return 2;
    }
    printf("cairo %s rendered and read back ARGB32 pixel 0x%08x\n",
           cairo_version_string(), pixel);
    return 0;
}
