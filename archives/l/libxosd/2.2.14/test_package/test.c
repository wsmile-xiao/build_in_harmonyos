/* libxosd 2.2.14 consumer link + load smoke test (display-free).
 *
 * xosd is an X11 overlay library; without an X server we cannot create a
 * display object.  Instead we prove the library links and loads and that its
 * public API surface is intact by:
 *   - reading the osd_default_font / osd_default_colour global externs
 *     (no X server required), and
 *   - taking the address of xosd_set_bar_length (resolves the symbol against
 *     libxosd and its transitive X11 / Xext / Xinerama dependencies).
 */

#include <xosd.h>
#include <stdio.h>

int main(void) {
    /* 1. Library data symbols — prove the shared object loaded and the
     *    public configuration externs are exported. */
    const char *font = osd_default_font;
    const char *colour = osd_default_colour;
    printf("xosd default_font=%s default_colour=%s\n",
           font ? font : "(null)", colour ? colour : "(null)");

    /* 2. Library function symbol — the linker must resolve it against
     *    libxosd and pull in the transitive X11 / Xext / Xinerama libs. */
    int (*fn)(xosd *, int) = xosd_set_bar_length;
    if (fn == 0) {
        fprintf(stderr, "xosd_set_bar_length symbol not resolved\n");
        return 2;
    }
    return 0;
}
