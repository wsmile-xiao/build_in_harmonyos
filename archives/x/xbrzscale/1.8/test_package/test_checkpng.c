// test_checkpng.c — loads a PNG via SDL2_image and asserts its dimensions:
// usage: test_checkpng <file> <expected_w> <expected_h>.
#include <stdio.h>
#include <stdlib.h>

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
    if (argc != 4) {
        fprintf(stderr, "usage: test_checkpng <file> <expected_w> <expected_h>\n");
        return 2;
    }
    int want_w = atoi(argv[2]);
    int want_h = atoi(argv[3]);
    if (SDL_Init(SDL_INIT_VIDEO) != 0) {
        fprintf(stderr, "SDL_Init failed: %s\n", SDL_GetError());
        return 1;
    }
    if ((IMG_Init(IMG_INIT_PNG) & IMG_INIT_PNG) == 0) {
        fprintf(stderr, "IMG_Init PNG failed: %s\n", IMG_GetError());
        SDL_Quit();
        return 1;
    }
    SDL_Surface *s = IMG_Load(argv[1]);
    if (!s) {
        fprintf(stderr, "IMG_Load(%s) failed: %s\n", argv[1], IMG_GetError());
        IMG_Quit();
        SDL_Quit();
        return 1;
    }
    printf("%s: %dx%d\n", argv[1], s->w, s->h);
    int ok = (s->w == want_w && s->h == want_h);
    SDL_FreeSurface(s);
    IMG_Quit();
    SDL_Quit();
    return ok ? 0 : 1;
}
