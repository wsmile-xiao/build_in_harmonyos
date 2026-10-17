#include <SDL.h>
#include <SDL_mixer.h>
#include <stdio.h>

int main(void) {
    if (SDL_Init(0) != 0) return 1;
    if (Mix_Init(0) != 0) return 2;
    if (Mix_AllocateChannels(4) != 4) return 3;
    Mix_Quit();
    SDL_Quit();
    puts("SDL_mixer API test passed");
    return 0;
}
