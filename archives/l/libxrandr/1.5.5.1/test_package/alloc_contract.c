/* Display-independent ABI + allocation contract test for libXrandr.
 *
 * Exercises alloc/free API pairs that need no X server connection and
 * verifies the public XRR struct layout/version macros, matching the
 * libXrandr.so.2.2.0 (SOVERSION 2) ABI shipped by upstream 1.5.5.
 */
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#include <X11/Xlib.h>
#include <X11/extensions/Xrandr.h>
#include <X11/extensions/randr.h>

int main(void)
{
    /* ── Version macros from randr.h / xorgproto ── */
#if defined(RANDR_MAJOR) && defined(RANDR_MINOR)
    if (RANDR_MAJOR < 1 || RANDR_MINOR < 5) {
        fprintf(stderr, "RANDR protocol version too old: %d.%d\n",
                RANDR_MAJOR, RANDR_MINOR);
        return 1;
    }
#else
    fprintf(stderr, "RANDR_MAJOR/RANDR_MINOR macros missing\n");
    return 2;
#endif

    /* ── XRRModeInfo layout (upstream 1.5.5 ABI) ── */
    {
        XRRModeInfo *mi = XRRAllocModeInfo("1920x1080", 8);
        if (mi == NULL) {
            fprintf(stderr, "XRRAllocModeInfo returned NULL\n");
            return 3;
        }
        if (mi->nameLength != 8 || strncmp(mi->name, "1920x1080", 8) != 0) {
            fprintf(stderr, "XRRAllocModeInfo name round-trip failed\n");
            XRRFreeModeInfo(mi);
            return 4;
        }
        mi->id = 0x42;
        mi->width = 1920;
        mi->height = 1080;
        if (mi->id != 0x42 || mi->width != 1920 || mi->height != 1080) {
            fprintf(stderr, "XRRModeInfo field assignment failed\n");
            XRRFreeModeInfo(mi);
            return 5;
        }
        XRRFreeModeInfo(mi);
    }

    /* ── XRRCrtcGamma allocation contract (XRRAllocGamma) ── */
    {
        XRRCrtcGamma *g = XRRAllocGamma(256);
        if (g == NULL) {
            fprintf(stderr, "XRRAllocGamma returned NULL\n");
            return 6;
        }
        if (g->size != 256 || g->red == NULL || g->green == NULL ||
            g->blue == NULL) {
            fprintf(stderr, "XRRAllocGamma layout broken\n");
            XRRFreeGamma(g);
            return 7;
        }
        /* red/green/blue must be contiguous in one allocation */
        if ((size_t)(g->green - g->red) != 256 ||
            (size_t)(g->blue - g->green) != 256) {
            fprintf(stderr, "XRRAllocGamma channel stride broken\n");
            XRRFreeGamma(g);
            return 8;
        }
        g->red[0] = 0;
        g->red[255] = 0xffff;
        g->green[128] = 0x7fff;
        g->blue[64] = 0x3fff;
        if (g->red[0] != 0 || g->red[255] != 0xffff ||
            g->green[128] != 0x7fff || g->blue[64] != 0x3fff) {
            fprintf(stderr, "XRRAllocGamma channel write-back failed\n");
            XRRFreeGamma(g);
            return 9;
        }
        XRRFreeGamma(g);
    }

    /* ── XRRScreenSize / XRRModeFlags layout sanity ── */
    {
        XRRScreenSize s;
        memset(&s, 0, sizeof(s));
        s.width = 1920;
        s.height = 1080;
        s.mwidth = 508;
        s.mheight = 286;
        if (sizeof(s.width) != sizeof(int) || sizeof(s) < 4 * sizeof(int)) {
            fprintf(stderr, "XRRScreenSize layout unexpected\n");
            return 10;
        }
    }

    puts("LIBXRANDR_TEST alloc_contract PASS");
    return 0;
}
