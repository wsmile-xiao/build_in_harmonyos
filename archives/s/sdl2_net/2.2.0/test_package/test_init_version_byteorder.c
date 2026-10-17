#include "test_common.h"

#include <string.h>

int main(void)
{
    SDLNet_version compiled;
    const SDLNet_version *linked;
    Uint8 word[2] = {0, 0};
    Uint8 dword[4] = {0, 0, 0, 0};
    int status = 1;

    if (test_runtime_init() < 0) {
        return 1;
    }

    SDL_NET_VERSION(&compiled);
    linked = SDLNet_Linked_Version();
    if (linked == NULL || linked->major != compiled.major ||
        linked->minor != compiled.minor || linked->patch != compiled.patch) {
        fprintf(stderr, "Compiled and linked SDL2_net versions differ\n");
        goto cleanup;
    }
    if (linked->major != 2 || linked->minor != 2 || linked->patch != 0) {
        fprintf(stderr, "Unexpected SDL2_net linked version\n");
        goto cleanup;
    }

    SDLNet_Write16(0x1234u, word);
    if (word[0] != 0x12u || word[1] != 0x34u ||
        SDLNet_Read16(word) != 0x1234u) {
        fprintf(stderr, "16-bit network byte order conversion failed\n");
        goto cleanup;
    }

    SDLNet_Write32(0x12345678u, dword);
    if (dword[0] != 0x12u || dword[1] != 0x34u ||
        dword[2] != 0x56u || dword[3] != 0x78u ||
        SDLNet_Read32(dword) != 0x12345678u) {
        fprintf(stderr, "32-bit network byte order conversion failed\n");
        goto cleanup;
    }

    status = 0;

cleanup:
    test_runtime_quit();
    return status;
}
