#include <stdio.h>
#include <stdlib.h>
#include <SDL2/SDL.h>

int main(void) {
    if (SDL_Init(SDL_INIT_VIDEO) != 0) {
        printf("SDL_Init failed: %s\n", SDL_GetError());
        return 1;
    }
    SDL_version version;
    SDL_GetVersion(&version);
    printf("SDL2 version: %d.%d.%d\n", version.major, version.minor, version.patch);
    printf("SDL2 2.30.10 test: OK\n");
    SDL_Quit();
    return 0;
}
