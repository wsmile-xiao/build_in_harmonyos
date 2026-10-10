#include <stdio.h>
#include <stdlib.h>
#include <playerctl/playerctl.h>
#include <playerctl/playerctl-player-manager.h>
#include <glib.h>

/* End-to-end consumer of the libplayerctl API.
 *
 * playerctl talks to media players over MPRIS (a D-Bus interface). On a headless
 * OHOS PC there is no D-Bus session bus, so playerctl_player_manager_new() returns
 * NULL with a GError instead of crashing. The test verifies the library is correctly
 * linked and its public constructor / type API is reachable — the real integration
 * point any downstream consumer depends on. */
int main(void) {
    GError *err = NULL;

    PlayerctlPlayerManager *manager = playerctl_player_manager_new(&err);
    if (manager == NULL) {
        /* Expected on a headless OHOS PC with no D-Bus session bus. */
        if (err != NULL) {
            g_printerr("playerctl: manager unavailable (no D-Bus session bus): %s\n",
                       err->message);
            g_error_free(err);
        }
    } else {
        /* If a bus were present, manage players here. Release the object. */
        g_object_unref(manager);
    }

    /* Reaching here means the library is correctly linked and its public API is
     * reachable. Exercise a second public symbol to confirm full symbol binding. */
    GType t = playerctl_player_manager_get_type();
    printf("LIBPLAYERCTL_CONSUMER_OK: library linked, public API reachable (type=%lu)\n",
           (unsigned long) t);
    return 0;
}
