#ifndef SDL2_NET_TEST_COMMON_H
#define SDL2_NET_TEST_COMMON_H

#ifndef SDL_MAIN_HANDLED
#define SDL_MAIN_HANDLED
#endif

#include <SDL.h>
#include <SDL_net.h>

#include <stdio.h>

static inline int test_runtime_init(void)
{
    SDL_SetMainReady();
    if (SDL_Init(0) < 0) {
        fprintf(stderr, "SDL_Init failed: %s\n", SDL_GetError());
        return -1;
    }
    if (SDLNet_Init() < 0) {
        fprintf(stderr, "SDLNet_Init failed: %s\n", SDLNet_GetError());
        SDL_Quit();
        return -1;
    }
    return 0;
}

static inline void test_runtime_quit(void)
{
    SDLNet_Quit();
    SDL_Quit();
}

static inline void test_report_net_error(const char *operation)
{
    fprintf(stderr, "%s failed: %s\n", operation, SDLNet_GetError());
}

static inline int test_udp_loopback_target(UDPsocket socket, IPaddress *target)
{
    IPaddress *bound = SDLNet_UDP_GetPeerAddress(socket, -1);
    Uint16 port;

    if (bound == NULL) {
        test_report_net_error("SDLNet_UDP_GetPeerAddress");
        return -1;
    }
    port = SDLNet_Read16(&bound->port);
    if (port == 0 || SDLNet_ResolveHost(target, "127.0.0.1", port) < 0) {
        test_report_net_error("SDLNet_ResolveHost(loopback)");
        return -1;
    }
    return 0;
}

#endif
