/*
 * test_package consumer test for gdk-pixbuf 2.44.6.1.1.
 *
 * Exercises the real gdk-pixbuf public API (R34 — no shell/print-only tests):
 *   - gdk_pixbuf_new():              creates a GdkPixbuf
 *   - gdk_pixbuf_get_width/height(): reads back the pixel buffer dimensions
 *   - gdk_pixbuf_get_has_alpha():    reads the alpha flag
 */
#include <gdk-pixbuf/gdk-pixbuf.h>
#include <stdio.h>

int main(void)
{
    GdkPixbuf *pixbuf = gdk_pixbuf_new (GDK_COLORSPACE_RGB, TRUE, 8, 16, 16);
    if (pixbuf == NULL)
    {
        fprintf (stderr, "FAIL: gdk_pixbuf_new() returned NULL\n");
        return 1;
    }

    int width = gdk_pixbuf_get_width (pixbuf);
    int height = gdk_pixbuf_get_height (pixbuf);
    int has_alpha = gdk_pixbuf_get_has_alpha (pixbuf);
    int n_channels = gdk_pixbuf_get_n_channels (pixbuf);
    g_object_unref (pixbuf);

    if (width != 16 || height != 16)
    {
        fprintf (stderr, "FAIL: unexpected pixbuf size %dx%d (expected 16x16)\n", width, height);
        return 1;
    }

    printf ("gdk-pixbuf 2.44.6.1.1 OK: %dx%d channels=%d has_alpha=%d\n",
            width, height, n_channels, has_alpha);
    return 0;
}
