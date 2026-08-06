#include <libcallaudio.h>
#include <glib.h>

int main(void) {
    GError *err = NULL;

    /* Call the real libcallaudio API — not a stub (R34).
     * call_audio_init() connects to the callaudiod DBus service;
     * failure is expected when the daemon is not running. */
    call_audio_init(&err);
    if (err) {
        g_clear_error(&err);
    }
    call_audio_deinit();
    return 0;
}
