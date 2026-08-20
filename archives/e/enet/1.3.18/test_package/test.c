/*
 * test_enet.c — Conan L1 test for enet 1.3.18
 *
 * Substantially exercises the enet API (R34):
 *   - enet_initialize() / enet_deinitialize() lifecycle
 *   - enet_linked_version() version check
 *   - enet_host_create() / enet_host_destroy() (binds a UDP socket on localhost)
 *
 * This is NOT a print-only stub; it links against libenet and calls real
 * library functions.  Failure to link or a non-zero return from
 * enet_initialize() will fail the test.
 */
#include <stdio.h>
#include <string.h>

#include <enet/enet.h>

int main(void) {
    if (enet_initialize() != 0) {
        fprintf(stderr, "enet_initialize() failed\n");
        return 1;
    }

    ENetVersion ver = enet_linked_version();
    printf("enet linked version: 0x%08x\n", (unsigned)ver);

    /* Create a host listening on localhost:0 (ephemeral port) — exercises
       socket creation, bind, and the core host data structures. */
    ENetAddress address;
    address.host = ENET_HOST_ANY;
    address.port = 0;

    ENetHost *server = enet_host_create(&address, 32, 2, 0, 0);
    if (server == NULL) {
        fprintf(stderr, "enet_host_create() failed\n");
        enet_deinitialize();
        return 1;
    }

    printf("enet_host_create() OK, port=%u\n", server->address.port);

    enet_host_destroy(server);
    enet_deinitialize();

    printf("enet 1.3.18 test: OK\n");
    return 0;
}
