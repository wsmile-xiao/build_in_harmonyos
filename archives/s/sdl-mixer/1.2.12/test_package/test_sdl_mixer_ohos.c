#include <SDL.h>
#include <SDL_mixer.h>
#include <stdio.h>

int main(void) {
    if (SDL_Init(SDL_INIT_AUDIO | SDL_INIT_VIDEO) != 0) return 1;
    if (!SDL_VideoDriverName(NULL, 0) || !SDL_AudioDriverName(NULL, 0)) return 2;
    if (Mix_OpenAudio(22050, AUDIO_S16SYS, 2, 512) != 0) return 3;
    int frequency = 0, channels = 0;
    Uint16 format = 0;
    if (!Mix_QuerySpec(&frequency, &format, &channels)) return 4;
    if (frequency != 22050 || channels != 2) return 5;
    Mix_CloseAudio();
    SDL_Quit();
    puts("HarmonyOS headless SDL_mixer test passed");
    return 0;
}
