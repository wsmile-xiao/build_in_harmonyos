#include <chafa.h>
#include <glib.h>

#include <string.h>

int main(void) {
    if (CHAFA_MAJOR_VERSION != 1 || CHAFA_MINOR_VERSION != 18) {
        return 1;
    }

    ChafaCanvasConfig *config = chafa_canvas_config_new();
    if (config == NULL) {
        return 2;
    }

    chafa_canvas_config_set_geometry(config, 4, 2);
    chafa_canvas_config_set_canvas_mode(config, CHAFA_CANVAS_MODE_FGBG);

    ChafaCanvas *canvas = chafa_canvas_new(config);
    if (canvas == NULL) {
        chafa_canvas_config_unref(config);
        return 3;
    }

    const guint8 pixels[] = {
        0xff, 0x00, 0x00,  0x00, 0xff, 0x00,  0x00, 0x00, 0xff,  0xff, 0xff, 0xff,
        0x00, 0x00, 0x00,  0x40, 0x40, 0x40,  0x80, 0x80, 0x80,  0xc0, 0xc0, 0xc0,
        0xff, 0xff, 0x00,  0x00, 0xff, 0xff,  0xff, 0x00, 0xff,  0x20, 0x40, 0x60,
        0x60, 0x40, 0x20,  0x10, 0x70, 0xd0,  0xd0, 0x70, 0x10,  0x33, 0x66, 0x99,
    };

    chafa_canvas_draw_all_pixels(canvas, CHAFA_PIXEL_RGB8, pixels, 4, 4, 12);

    ChafaTermInfo *term_info = chafa_term_info_new();
    if (term_info == NULL) {
        chafa_canvas_unref(canvas);
        chafa_canvas_config_unref(config);
        return 4;
    }

    GString *printed = chafa_canvas_print(canvas, term_info);
    if (printed == NULL || printed->len == 0) {
        if (printed != NULL) {
            g_string_free(printed, TRUE);
        }
        chafa_term_info_unref(term_info);
        chafa_canvas_unref(canvas);
        chafa_canvas_config_unref(config);
        return 5;
    }

    if (strstr(printed->str, "\n") == NULL) {
        g_string_free(printed, TRUE);
        chafa_term_info_unref(term_info);
        chafa_canvas_unref(canvas);
        chafa_canvas_config_unref(config);
        return 6;
    }

    g_string_free(printed, TRUE);
    chafa_term_info_unref(term_info);
    chafa_canvas_unref(canvas);
    chafa_canvas_config_unref(config);
    return 0;
}
