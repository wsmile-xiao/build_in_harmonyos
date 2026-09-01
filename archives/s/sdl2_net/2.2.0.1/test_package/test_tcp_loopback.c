#include "test_common.h"

#include <string.h>

static TCPsocket open_loopback_server(Uint16 *selected_port)
{
    Uint32 seed = SDL_GetTicks();
    int attempt;

    for (attempt = 0; attempt < 128; ++attempt) {
        Uint16 port = (Uint16)(30000u + ((seed + (Uint32)attempt) % 20000u));
        IPaddress address;
        TCPsocket server;

        if (SDLNet_ResolveHost(&address, NULL, port) < 0) {
            continue;
        }
        server = SDLNet_TCP_Open(&address);
        if (server != NULL) {
            *selected_port = port;
            return server;
        }
    }
    return NULL;
}

static int receive_exact(TCPsocket socket, void *buffer, int length)
{
    Uint8 *cursor = (Uint8 *)buffer;
    SDLNet_SocketSet set = NULL;
    int total = 0;
    int added = 0;
    int result = -1;

    set = SDLNet_AllocSocketSet(1);
    if (set == NULL || SDLNet_TCP_AddSocket(set, socket) != 1) {
        goto cleanup;
    }
    added = 1;

    while (total < length) {
        if (SDLNet_CheckSockets(set, 2000) != 1 ||
            !SDLNet_SocketReady(socket)) {
            goto cleanup;
        }
        int received = SDLNet_TCP_Recv(socket, cursor + total, length - total);
        if (received <= 0) {
            goto cleanup;
        }
        total += received;
    }
    result = total;

cleanup:
    if (added) {
        SDLNet_TCP_DelSocket(set, socket);
    }
    SDLNet_FreeSocketSet(set);
    return result;
}

int main(void)
{
    static const char request[] = "sdl2-net-tcp-request";
    static const char response[] = "sdl2-net-tcp-response";
    char request_buffer[sizeof(request)];
    char response_buffer[sizeof(response)];
    TCPsocket server = NULL;
    TCPsocket client = NULL;
    TCPsocket accepted = NULL;
    IPaddress remote;
    Uint16 port = 0;
    Uint32 started;
    int status = 1;

    if (test_runtime_init() < 0) {
        return 1;
    }

    server = open_loopback_server(&port);
    if (server == NULL || port == 0) {
        test_report_net_error("SDLNet_TCP_Open(server)");
        goto cleanup;
    }
    if (SDLNet_TCP_GetPeerAddress(server) != NULL) {
        fprintf(stderr, "Server socket unexpectedly has a peer address\n");
        goto cleanup;
    }

    if (SDLNet_ResolveHost(&remote, "127.0.0.1", port) < 0) {
        test_report_net_error("SDLNet_ResolveHost(loopback)");
        goto cleanup;
    }
    client = SDLNet_TCP_Open(&remote);
    if (client == NULL) {
        test_report_net_error("SDLNet_TCP_Open(client)");
        goto cleanup;
    }

    started = SDL_GetTicks();
    while ((SDL_GetTicks() - started) < 2000u) {
        accepted = SDLNet_TCP_Accept(server);
        if (accepted != NULL) {
            break;
        }
        SDL_Delay(5);
    }
    if (accepted == NULL || SDLNet_TCP_GetPeerAddress(client) == NULL ||
        SDLNet_TCP_GetPeerAddress(accepted) == NULL) {
        test_report_net_error("SDLNet_TCP_Accept");
        goto cleanup;
    }

    if (SDLNet_TCP_Send(client, request, (int)sizeof(request)) !=
            (int)sizeof(request) ||
        receive_exact(accepted, request_buffer, (int)sizeof(request)) !=
            (int)sizeof(request) ||
        memcmp(request_buffer, request, sizeof(request)) != 0) {
        fprintf(stderr, "TCP client-to-server transfer failed\n");
        goto cleanup;
    }

    if (SDLNet_TCP_Send(accepted, response, (int)sizeof(response)) !=
            (int)sizeof(response) ||
        receive_exact(client, response_buffer, (int)sizeof(response)) !=
            (int)sizeof(response) ||
        memcmp(response_buffer, response, sizeof(response)) != 0) {
        fprintf(stderr, "TCP server-to-client transfer failed\n");
        goto cleanup;
    }

    status = 0;

cleanup:
    SDLNet_TCP_Close(accepted);
    SDLNet_TCP_Close(client);
    SDLNet_TCP_Close(server);
    test_runtime_quit();
    return status;
}
