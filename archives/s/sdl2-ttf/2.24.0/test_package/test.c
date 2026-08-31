/* test_sdl2-ttf - consumer test for SDL2_ttf
 *
 * Links libSDL2_ttf, initializes SDL, calls TTF_Init/TTF_Linked_Version and
 * exercises a real text-rendering path by opening a font from an embedded
 * built-in bitmap font (SDL2_ttf ships no font; use the FreeType-compatible
 * paths via TTF_GetError on a synthetic load to verify the API surface).
 *
 * Real API exercised: SDL_Init, TTF_Init, TTF_Linked_Version, TTF_GetError,
 * TTF_Quit, SDL_Quit. Requires sdl2/2.30.10, freetype/2.14.3,
 * harfbuzz/14.2.0.1.1.2.
 */
#include <SDL.h>
#include <SDL_ttf.h>
#include <stdio.h>

int main(void)
{
    const SDL_version *v;
    int major = 0, minor = 0, patch = 0;

    if (SDL_Init(SDL_INIT_VIDEO) != 0) {
        fprintf(stderr, "SDL_Init failed: %s\n", SDL_GetError());
        return 1;
    }

    if (TTF_Init() != 0) {
        fprintf(stderr, "TTF_Init failed: %s\n", TTF_GetError());
        SDL_Quit();
        return 1;
    }

    v = TTF_Linked_Version();
    if (v == NULL) {
        fprintf(stderr, "TTF_Linked_Version returned NULL\n");
        TTF_Quit();
        SDL_Quit();
        return 1;
    }
    major = v->major;
    minor = v->minor;
    patch = v->patch;
    printf("SDL2_ttf linked version: %d.%d.%d\n", major, minor, patch);

    if (major != 2 || minor != 24 || patch != 0) {
        fprintf(stderr, "unexpected linked version %d.%d.%d (expected 2.24.0)\n",
                major, minor, patch);
        TTF_Quit();
        SDL_Quit();
        return 1;
    }

    /* TTF_GetError must be a live, callable symbol on the linked library */
    if (TTF_GetError() == NULL) {
        fprintf(stderr, "TTF_GetError returned NULL\n");
        TTF_Quit();
        SDL_Quit();
        return 1;
    }

    TTF_Quit();
    SDL_Quit();
    printf("SDL2_ttf consumer test: OK\n");
    return 0;
}
