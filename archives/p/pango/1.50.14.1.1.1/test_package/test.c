#include <pango/pangocairo.h>
#include <dlfcn.h>
#include <stdio.h>
#include <string.h>

#ifndef TARGET_SO
#define TARGET_SO "libpangocairo-1.0.so"
#endif

int main(void) {
    const char *ver = pango_version_string();
    if (!ver || !ver[0]) {
        fprintf(stderr, "pango_version_string failed\n");
        return 1;
    }

    PangoFontMap *map = pango_cairo_font_map_get_default();
    if (!map) {
        fprintf(stderr, "pango_cairo_font_map_get_default failed\n");
        return 1;
    }

    PangoContext *ctx = pango_font_map_create_context(map);
    if (!ctx) {
        fprintf(stderr, "pango_font_map_create_context failed\n");
        return 1;
    }
    g_object_unref(ctx);

    void *handle = dlopen(TARGET_SO, RTLD_NOW);
    if (!handle) {
        fprintf(stderr, "dlopen(%s) failed: %s\n", TARGET_SO, dlerror());
        return 2;
    }
    dlclose(handle);

    printf("pango ok version=%s (pangocairo)\n", ver);
    return 0;
}
