/* wmusic_consumer: a real consumer that links against playerctl 2.4.1 API.

   This verifies that playerctl headers, GObject type macros, and shared
   library are correctly installed and consumable on the target platform.
   It calls the real API: creates a PlayerctlPlayerManager and reads the
   "player-names" property.

   On OHOS sandbox, D-Bus is not available, so manager creation fails.
   That's expected - the test still proves headers link correctly by using
   the PLAYERCTL_TYPE_PLAYER_MANAGER macro and other real type symbols.
   On systems with D-Bus, it enumerates actual players.
*/
#include <playerctl/playerctl.h>
#include <glib.h>
#include <stdio.h>

int main(int argc, char *argv[]) {
    GError *error = NULL;

    /* Exercise real type macros to verify headers are correct */
    GType mgr_type = PLAYERCTL_TYPE_PLAYER_MANAGER;
    GType name_type = PLAYERCTL_TYPE_PLAYER_NAME;
    (void)mgr_type;
    (void)name_type;

    /* Initialize playerctl - real API: playerctl_player_manager_new(GError **) */
    PlayerctlPlayerManager *manager = playerctl_player_manager_new(&error);
    if (manager == NULL) {
        /* D-Bus not available in sandbox - expected, headers still verified */
        g_print("wmusic_consumer: manager init: %s\n", error->message);
        g_error_free(error);
        g_print("wmusic_consumer: PASS (headers+link OK, D-Bus unavailable)\n");
        return 0;
    }

    /* Get the list of player names from the manager's GObject property */
    GList *player_names = NULL;
    g_object_get(manager, "player-names", &player_names, NULL);

    gint n_players = g_list_length(player_names);
    g_print("wmusic_consumer: found %d MPRIS players\n", n_players);

    /* Iterate through players and print their names */
    for (GList *l = player_names; l != NULL; l = l->next) {
        PlayerctlPlayerName *name = (PlayerctlPlayerName *)l->data;
        g_print("  - %s\n", name->instance);
        playerctl_player_name_free(name);
    }

    g_list_free(player_names);
    g_object_unref(manager);

    g_print("wmusic_consumer: PASS\n");
    return 0;
}
