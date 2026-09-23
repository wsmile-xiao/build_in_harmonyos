#include <cairo.h>
#include <dlfcn.h>
#include <stdio.h>
#include <string.h>
#ifndef TARGET_SO
#define TARGET_SO "libcairo.so"
#endif
int main(void) {
    /* R34: 真实调用被测包 API（非仅 dlopen） */
    const char *ver = cairo_version_string();
    if (ver == NULL || strlen(ver) == 0) {
        fprintf(stderr, "cairo_version_string failed\n");
        return 1;
    }
    printf("cairo version: %s (%d)\n", ver, cairo_version());
    cairo_surface_t *s = cairo_image_surface_create(CAIRO_FORMAT_ARGB32, 16, 16);
    if (cairo_surface_status(s) != CAIRO_STATUS_SUCCESS) {
        fprintf(stderr, "cairo_image_surface_create failed: %s\n",
                cairo_status_to_string(cairo_surface_status(s)));
        return 1;
    }
    cairo_t *cr = cairo_create(s);
    cairo_set_source_rgb(cr, 1.0, 0.0, 0.0);
    cairo_paint(cr);
    cairo_destroy(cr);
    cairo_surface_destroy(s);
    printf("cairo: surface create/paint ok\n");
    /* 运行期可加载校验（制品仓 .so 动态加载） */
    void *h = dlopen(TARGET_SO, RTLD_NOW | RTLD_GLOBAL);
    if (!h) { fprintf(stderr, "dlopen %s failed: %s\n", TARGET_SO, dlerror()); return 1; }
    printf("cairo: dlopen %s ok\n", TARGET_SO);
    dlclose(h);
    return 0;
}
