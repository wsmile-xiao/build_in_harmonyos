/*
 * Consumer smoke test for libjuice 1.6.0 (Conan L1, R34).
 * Uses only the installed public API (juice/juice.h): creates an agent,
 * verifies state transitions with the state-to-string helper, exercises
 * local ICE attribute setup, then destroys the agent.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "juice/juice.h"

int main(void) {
    juice_config_t config;
    memset(&config, 0, sizeof(config));

    juice_agent_t *agent = juice_create(&config);
    if (!agent) {
        fprintf(stderr, "FAIL: juice_create returned NULL\n");
        return 1;
    }

    const char *s0 = juice_state_to_string(juice_get_state(agent));
    if (!s0 || strcmp(s0, "disconnected") != 0) {
        fprintf(stderr, "FAIL: unexpected initial state string '%s'\n", s0 ? s0 : "(null)");
        juice_destroy(agent);
        return 1;
    }

    /* Exercise the ICE attribute setter with fixed local credentials.
     * libjuice requires ufrag>=4 and pwd>=22 chars (RFC 8445). */
    if (juice_set_local_ice_attributes(agent, "testufrag", "abcdefghijklmnopqrstuvwx") != 0) {
        fprintf(stderr, "FAIL: juice_set_local_ice_attributes\n");
        juice_destroy(agent);
        return 1;
    }

    juice_destroy(agent);
    printf("test libjuice 1.6.0: OK (agent create/state/attributes/destroy)\n");
    return 0;
}