#include <cairo-gobject.h>
#include <cairo.h>
#include <glib-object.h>

int main(void) {
    if (cairo_gobject_context_get_type() == G_TYPE_INVALID) {
        return 1;
    }
    if (cairo_gobject_surface_get_type() == G_TYPE_INVALID) {
        return 2;
    }

    cairo_surface_t *surface = cairo_image_surface_create(CAIRO_FORMAT_ARGB32, 4, 4);
    if (surface == NULL) {
        return 3;
    }
    if (cairo_surface_status(surface) != CAIRO_STATUS_SUCCESS) {
        cairo_surface_destroy(surface);
        return 4;
    }

    cairo_t *context = cairo_create(surface);
    if (context == NULL) {
        cairo_surface_destroy(surface);
        return 5;
    }
    cairo_set_source_rgb(context, 0.0, 0.0, 0.0);
    cairo_paint(context);
    cairo_destroy(context);
    cairo_surface_destroy(surface);
    return 0;
}
