/**
 * test_package for SDL2 2.30.0
 *
 * Verifies that SDL2 headers are found, the library links correctly,
 * and basic SDL2 API functions are callable at runtime.
 *
 * R34: Test must substantially depend on the tested package — this file
 * calls SDL_GetVersion(), SDL_Init(), and SDL_Quit() from SDL2.
 */
#include <stdio.h>
#include "SDL.h"

int main(void) {
    SDL_version compiled;
    SDL_version linked;

    /* Verify compile-time version macro (SDL_VERSION) */
    SDL_VERSION(&compiled);
    printf("SDL compiled version: %u.%u.%u\n",
           compiled.major, compiled.minor, compiled.patch);

    /* Verify runtime linking (SDL_GetVersion) */
    SDL_GetVersion(&linked);
    printf("SDL linked version:  %u.%u.%u\n",
           linked.major, linked.minor, linked.patch);

    /* Verify compiled and linked versions match */
    if (compiled.major != linked.major ||
        compiled.minor != linked.minor ||
        compiled.patch != linked.patch) {
        fprintf(stderr, "ERROR: compiled SDL version (%u.%u.%u) does not match "
                        "linked version (%u.%u.%u)\n",
                compiled.major, compiled.minor, compiled.patch,
                linked.major, linked.minor, linked.patch);
        return 1;
    }
    printf("SDL version match: OK\n");

    /* Verify SDL_Init with no subsystems (should succeed on any platform) */
    if (SDL_Init(0) < 0) {
        fprintf(stderr, "ERROR: SDL_Init(0) failed: %s\n", SDL_GetError());
        return 1;
    }
    printf("SDL_Init(0): OK\n");

    /* Clean shutdown */
    SDL_Quit();
    printf("SDL_Quit(): OK\n");

    printf("All SDL2 tests passed.\n");
    return 0;
}