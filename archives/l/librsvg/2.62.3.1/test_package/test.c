#include <librsvg/rsvg.h>
#include <stdio.h>
#include <string.h>

int main(void) {
    /* 核验 librsvg 版本常量可编译 */
    const char *ver = LIBRSVG_VERSION;
    printf("librsvg version string: %s\n", ver);

    /* 构造一个最小 SVG，用 rsvg_handle_new_from_data 解析 */
    const char *svg =
        "<svg xmlns=\"http://www.w3.org/2000/svg\""
        " width=\"10\" height=\"10\"><rect"
        " x=\"0\" y=\"0\" width=\"10\" height=\"10\""
        " fill=\"red\"/></svg>";
    size_t len = strlen(svg);
    GError *err = NULL;
    RsvgHandle *handle = rsvg_handle_new_from_data(
        (const guint8 *)svg, (gsize)len, &err);
    if (handle == NULL) {
        fprintf(stderr, "rsvg_handle_new_from_data failed: %s\n",
                err ? err->message : "unknown");
        if (err) g_error_free(err);
        return 1;
    }
    printf("rsvg_handle_new_from_data: ok\n");
    g_object_unref(handle);
    return 0;
}
