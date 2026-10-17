#include <stdio.h>

/* Include the library's public header — verifies the include path
 * and that the header parses against the installed libxcb headers. */
#include <xcb/xcb.h>
#include <xcb/render.h>
#include <xcb/xcb_renderutil.h>

int main(void) {
    /* Smoke test: call functions that are safe without a live X connection.
     *
     * xcb_render_util_find_visual_format with NULL formats reply returns 0
     * (checked in source: "if (!formats) return 0;").
     *
     * xcb_render_util_disconnect with NULL connection returns 0
     * (iterates linked list, finds no match).
     *
     * This proves the library is linked and the ABI surface is correct.
     */
    xcb_render_pictvisual_t *fmt =
        xcb_render_util_find_visual_format(NULL, 0);
    int disconnected = xcb_render_util_disconnect(NULL);

    int ok = (fmt == NULL) && (disconnected == 0);
    printf("test xcb-util-renderutil 0.3.10: %s (fmt=%p, disconnect=%d)\n",
           ok ? "OK" : "FAIL", (void *)fmt, disconnected);
    return ok ? 0 : 1;
}
