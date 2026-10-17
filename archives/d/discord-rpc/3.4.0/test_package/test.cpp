#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "discord_rpc.h"
#include "discord_register.h"

/* Real API exercise: initialize the SDK, set/clear presence, and run a short
 * callback loop. Expected to exit 0 without segfaulting. */
int main(void) {
    DiscordEventHandlers handlers;
    memset(&handlers, 0, sizeof(handlers));

    Discord_Initialize("123456789012345678", &handlers, 0, NULL);
    Discord_RunCallbacks();

    DiscordRichPresence presence;
    memset(&presence, 0, sizeof(presence));
    presence.state = "OHOS test";
    presence.details = "discord-rpc 3.4.0 conan test";
    Discord_UpdatePresence(&presence);
    Discord_RunCallbacks();

    Discord_ClearPresence();
    Discord_Shutdown();

    printf("test discord-rpc 3.4.0: OK\n");
    return 0;
}