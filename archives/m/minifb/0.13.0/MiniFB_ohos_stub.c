/* MiniFB_ohos_stub.c — OHOS headless backend (recipe-provided source).
 *
 * OHOS has no X11/Wayland session, so window creation cannot be
 * supported. The four window-dependent entry points referenced by the
 * platform-independent core (MiniFB_common.c) get headless
 * implementations here:
 *   - mfb_open_ex          -> NULL (documented: no window system)
 *   - mfb_update_ex        -> MFB_STATE_INVALID_WINDOW
 *   - mfb_set_viewport     -> no-op returning false
 *   - mfb_get_monitor_scale-> no-op returning false
 * Everything else (timers via MiniFB_linux.c, update state machine,
 * NULL-guarded input getters, utf8 helpers) links and runs headless.
 */
#include <stddef.h>
#include <MiniFB.h>

struct mfb_window *
mfb_open_ex(const char *title, unsigned width, unsigned height, unsigned flags) {
    (void) title; (void) width; (void) height; (void) flags;
    return NULL;  /* OHOS: no window system */
}

mfb_update_state
mfb_update_ex(struct mfb_window *window, void *buffer, unsigned width, unsigned height) {
    (void) buffer; (void) width; (void) height;
    if (window == NULL)
        return MFB_STATE_INVALID_WINDOW;
    return MFB_STATE_INTERNAL_ERROR;
}

bool
mfb_set_viewport(struct mfb_window *window, unsigned offset_x, unsigned offset_y, unsigned width, unsigned height) {
    (void) offset_x; (void) offset_y; (void) width; (void) height;
    (void) window;
    return false;  /* OHOS headless: no viewport */
}

void
mfb_get_monitor_scale(struct mfb_window *window, float *scale_x, float *scale_y) {
    if (scale_x) *scale_x = 1.0f;
    if (scale_y) *scale_y = 1.0f;
    (void) window;  /* OHOS headless: identity scale */
}
