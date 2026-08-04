#include <gio/gio.h>
#include <gdk-pixbuf/gdk-pixbuf.h>

#include <stdio.h>
#include <string.h>

static int checks = 0;

static int
require_true(gboolean condition, const char *message)
{
    checks++;
    if (!condition) {
        fprintf(stderr, "check %d failed: %s\n", checks, message);
        return 0;
    }
    return 1;
}

static gboolean
has_format(const char *name)
{
    GSList *formats = gdk_pixbuf_get_formats();
    GSList *item;
    gboolean found = FALSE;

    for (item = formats; item != NULL; item = item->next) {
        GdkPixbufFormat *format = item->data;
        char *format_name = gdk_pixbuf_format_get_name(format);
        if (g_strcmp0(format_name, name) == 0) {
            found = TRUE;
        }
        g_free(format_name);
        if (found) {
            break;
        }
    }
    g_slist_free(formats);
    return found;
}

int
main(void)
{
    GError *error = NULL;
    GdkPixbuf *pixbuf = gdk_pixbuf_new(GDK_COLORSPACE_RGB, TRUE, 8, 2, 2);
    GdkPixbuf *decoded;
    GdkPixbuf *scaled;
    GInputStream *stream;
    guchar *pixels;
    gchar *encoded = NULL;
    gsize encoded_size = 0;

    if (!require_true(pixbuf != NULL, "create RGBA pixbuf")) {
        return 1;
    }
    if (!require_true(gdk_pixbuf_get_width(pixbuf) == 2, "pixbuf width")) {
        return 2;
    }
    if (!require_true(gdk_pixbuf_get_height(pixbuf) == 2, "pixbuf height")) {
        return 3;
    }
    if (!require_true(gdk_pixbuf_get_has_alpha(pixbuf), "pixbuf alpha channel")) {
        return 4;
    }

    gdk_pixbuf_fill(pixbuf, 0x3366ccff);
    pixels = gdk_pixbuf_get_pixels(pixbuf);
    if (!require_true(
            pixels[0] == 0x33 && pixels[1] == 0x66 &&
                pixels[2] == 0xcc && pixels[3] == 0xff,
            "pixel fill result")) {
        return 5;
    }

    if (!require_true(has_format("png"), "PNG loader registered")) {
        return 6;
    }
    if (!require_true(has_format("jpeg"), "JPEG loader registered")) {
        return 7;
    }
    if (!require_true(has_format("tiff"), "TIFF loader registered")) {
        return 8;
    }
    if (!require_true(has_format("gif"), "GIF loader registered")) {
        return 9;
    }

    if (!require_true(
            gdk_pixbuf_save_to_buffer(
                pixbuf, &encoded, &encoded_size, "png", &error, NULL),
            error != NULL ? error->message : "PNG in-memory encoding")) {
        g_clear_error(&error);
        return 10;
    }
    if (!require_true(
            encoded_size > 8 && memcmp(encoded, "\x89PNG\r\n\x1a\n", 8) == 0,
            "PNG signature")) {
        return 11;
    }

    stream = g_memory_input_stream_new_from_data(encoded, encoded_size, NULL);
    decoded = gdk_pixbuf_new_from_stream(stream, NULL, &error);
    if (!require_true(
            decoded != NULL,
            error != NULL ? error->message : "PNG in-memory decoding")) {
        g_clear_error(&error);
        g_object_unref(stream);
        return 12;
    }
    if (!require_true(
            gdk_pixbuf_get_width(decoded) == 2 &&
                gdk_pixbuf_get_height(decoded) == 2,
            "decoded dimensions")) {
        return 13;
    }

    scaled = gdk_pixbuf_scale_simple(decoded, 4, 4, GDK_INTERP_BILINEAR);
    if (!require_true(scaled != NULL, "scale pixbuf")) {
        return 14;
    }
    if (!require_true(
            gdk_pixbuf_get_width(scaled) == 4 &&
                gdk_pixbuf_get_height(scaled) == 4,
            "scaled dimensions")) {
        return 15;
    }

    g_object_unref(scaled);
    g_object_unref(decoded);
    g_object_unref(stream);
    g_object_unref(pixbuf);
    g_free(encoded);
    printf("gdk-pixbuf consumer checks: %d/15 passed\n", checks);
    return 0;
}
