#include <SDL.h>
#include <stdio.h>

static int fail(const char *operation)
{
    fprintf(stderr, "%s failed: %s\n", operation, SDL_GetError());
    SDL_Quit();
    return 1;
}

int main(void)
{
    SDL_Surface *screen;
    SDL_Event pushed = {0};
    SDL_Event received = {0};
    Uint32 color;

    if (SDL_Init(SDL_INIT_VIDEO | SDL_INIT_TIMER) != 0) {
        return fail("SDL_Init");
    }
    screen = SDL_SetVideoMode(64, 48, 32, SDL_SWSURFACE);
    if (screen == NULL) {
        return fail("SDL_SetVideoMode");
    }
    color = SDL_MapRGB(screen->format, 12, 34, 56);
    if (SDL_FillRect(screen, NULL, color) != 0 || SDL_Flip(screen) != 0) {
        return fail("software rendering");
    }

    pushed.type = SDL_USEREVENT;
    pushed.user.code = 0xD006;
    if (SDL_PushEvent(&pushed) < 0) {
        return fail("SDL_PushEvent");
    }
    while (SDL_PollEvent(&received) == 1) {
        if (received.type == SDL_USEREVENT && received.user.code == 0xD006) {
            break;
        }
    }
    if (received.type != SDL_USEREVENT || received.user.code != 0xD006) {
        fprintf(stderr, "SDL event queue round trip failed\n");
        SDL_Quit();
        return 1;
    }

    SDL_Quit();
    puts("DXX-Rebirth SDL video, software rendering, and event path passed");
    return 0;
}
