#include <stdio.h>
#include <libxcvt/libxcvt.h>

#define CHECK(cond, msg)                                                     \
    do {                                                                     \
        if (!(cond)) {                                                       \
            fprintf(stderr, "FAIL: %s\n", msg);                              \
            return 1;                                                        \
        }                                                                    \
        printf("ok: %s\n", msg);                                             \
    } while (0)

int main(void) {
    /* RandR-compatible flag values (libxcvt_mode.h) */
    CHECK(LIBXCVT_MODE_FLAG_HSYNC_POSITIVE == (1 << 0), "HSYNC_POSITIVE == (1<<0)");
    CHECK(LIBXCVT_MODE_FLAG_HSYNC_NEGATIVE == (1 << 1), "HSYNC_NEGATIVE == (1<<1)");
    CHECK(LIBXCVT_MODE_FLAG_VSYNC_POSITIVE == (1 << 2), "VSYNC_POSITIVE == (1<<2)");
    CHECK(LIBXCVT_MODE_FLAG_VSYNC_NEGATIVE == (1 << 3), "VSYNC_NEGATIVE == (1<<3)");
    CHECK(LIBXCVT_MODE_FLAG_INTERLACE == (1 << 4), "INTERLACE == (1<<4)");

    /* ABI surface: the public struct is complete and usable */
    CHECK(sizeof(struct libxcvt_mode_info) > 0, "libxcvt_mode_info usable");
    CHECK(sizeof(((struct libxcvt_mode_info *)0)->dot_clock) == sizeof(uint64_t),
          "dot_clock is uint64_t");

    /* Behavior: a 1920x1080@60 CVT modeline is well-formed */
    struct libxcvt_mode_info *mode = libxcvt_gen_mode_info(
        1920, 1080, 60.0f, false, false);
    CHECK(mode != NULL, "gen_mode_info(1920x1080@60) non-NULL");
    CHECK(mode->hdisplay == 1920, "hdisplay == 1920");
    CHECK(mode->vdisplay == 1080, "vdisplay == 1080");
    CHECK(mode->htotal > mode->hdisplay, "htotal > hdisplay");
    CHECK(mode->vtotal > mode->vdisplay, "vtotal > vdisplay");
    CHECK(mode->dot_clock > 0, "dot_clock > 0");
    CHECK((mode->mode_flags & (LIBXCVT_MODE_FLAG_INTERLACE)) == 0,
          "interlaced flag clear for non-interlaced request");

    printf("libxcvt version contract: all checks passed\n");
    return 0;
}
