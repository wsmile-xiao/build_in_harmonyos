/* test_package/test.c - Conan L1 test for open62541
 * Verifies that the open62541 library can be linked and its API is usable.
 */
#include <open62541/server_config_default.h>
#include <stdio.h>
#include <stdlib.h>

int main(void) {
    UA_Server *server = UA_Server_new();
    if (server == NULL) {
        fprintf(stderr, "Failed to create UA_Server\n");
        return EXIT_FAILURE;
    }

    UA_ServerConfig *config = UA_Server_getConfig(server);
    if (config == NULL) {
        fprintf(stderr, "Failed to get server config\n");
        UA_Server_delete(server);
        return EXIT_FAILURE;
    }

    UA_StatusCode status = UA_ServerConfig_setMinimal(config, 4840, NULL);
    if (status != UA_STATUSCODE_GOOD) {
        fprintf(stderr, "Failed to set minimal config: %s\n", UA_StatusCode_name(status));
        UA_Server_delete(server);
        return EXIT_FAILURE;
    }

    printf("open62541 server created successfully\n");
    UA_Server_delete(server);

    printf("L1 test passed\n");
    return EXIT_SUCCESS;
}
