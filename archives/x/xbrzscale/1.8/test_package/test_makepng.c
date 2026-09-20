// test_makepng.c — writes a deterministic 8x8 RGBA PNG fixture for the
// xbrzscale CLI end-to-end test (exits 0 only if the file is created).
#include <stdio.h>

#if __has_include(<SDL2/SDL.h>)
#include <SDL2/SDL.h>
#else
#include <SDL.h>
#endif
#if __has_include(<SDL2/SDL_image.h>)
#include <SDL2/SDL_image.h>
#else
#include <SDL_image.h>
#endif

int main(int argc, char *argv[]) {
    const char *out = argc > 1 ? argv[1] : "input.png";
    if (SDL_Init(SDL_INIT_VIDEO) != 0) {
        fprintf(stderr, "SDL_Init failed: %s\n", SDL_GetError());
        return 1;
    }
    if ((IMG_Init(IMG_INIT_PNG) & IMG_INIT_PNG) == 0) {
        fprintf(stderr, "IMG_Init PNG failed: %s\n", IMG_GetError());
        SDL_Quit();
        return 1;
    }
    SDL_Surface *s = SDL_CreateRGBSurface(0, 8, 8, 32, 0xff0000U, 0xff00U, 0xffU, 0xff000000U);
    if (!s) {
        fprintf(stderr, "SDL_CreateRGBSurface failed: %s\n", SDL_GetError());
        IMG_Quit();
        SDL_Quit();
        return 1;
    }
    for (int y = 0; y < 8; ++y) {
        for (int x = 0; x < 8; ++x) {
            SDL_Rect r;
            r.x = x;
            r.y = y;
            r.w = 1;
            r.h = 1;
            Uint32 c = SDL_MapRGBA(s->format, (Uint8)((x * 32) & 0xff), (Uint8)((y * 32) & 0xff),
                                   (Uint8)(((x + y) * 16) & 0xff), 0xff);
            if (SDL_FillRect(s, &r, c) != 0) {
                fprintf(stderr, "SDL_FillRect failed: %s\n", SDL_GetError());
                SDL_FreeSurface(s);
                IMG_Quit();
                SDL_Quit();
                return 1;
            }
        }
    }
    if (IMG_SavePNG(s, out) != 0) {
        fprintf(stderr, "IMG_SavePNG failed: %s\n", IMG_GetError());
        SDL_FreeSurface(s);
        IMG_Quit();
        SDL_Quit();
        return 1;
    }
    SDL_FreeSurface(s);
    IMG_Quit();
    SDL_Quit();
    printf("wrote %s\n", out);
    return 0;
}
