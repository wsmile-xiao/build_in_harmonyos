/* SDL/SDL_mixer runtime consumer test for the lbreakout2 package.
 *
 * Mirrors the game's own startup sequence (client/main.c and gui/stk.c):
 * the exact SDL_Init subsystem set (video, audio, timer, joystick), the
 * 640x480x16 SDL_SWSURFACE display opened by stk_display_open(), software
 * rendering with a frame flip, the Mix_OpenAudio call from stk_audio_open(),
 * and the event queue used by the menu loop.
 */
#include <SDL.h>
#include <SDL_mixer.h>
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

    /* subsystem set requested by client/main.c::main() */
    if (SDL_Init(SDL_INIT_VIDEO | SDL_INIT_AUDIO | SDL_INIT_TIMER | SDL_INIT_JOYSTICK) != 0) {
        return fail("SDL_Init");
    }
    /* display mode opened by stk_display_open() */
    screen = SDL_SetVideoMode(640, 480, 16, SDL_SWSURFACE);
    if (screen == NULL) {
        return fail("SDL_SetVideoMode");
    }
    color = SDL_MapRGB(screen->format, 12, 34, 56);
    if (SDL_FillRect(screen, NULL, color) != 0 || SDL_Flip(screen) != 0) {
        return fail("software rendering");
    }

    /* audio path opened by stk_audio_open(); with the dummy audio driver
     * this must succeed even without a physical sound device */
    if (Mix_OpenAudio(22050, MIX_DEFAULT_FORMAT, 2, 4096) < 0) {
        fprintf(stderr, "Mix_OpenAudio failed: %s\n", Mix_GetError());
        SDL_Quit();
        return 1;
    }
    Mix_CloseAudio();

    pushed.type = SDL_USEREVENT;
    pushed.user.code = 0x0B02;
    if (SDL_PushEvent(&pushed) < 0) {
        return fail("SDL_PushEvent");
    }
    while (SDL_PollEvent(&received) == 1) {
        if (received.type == SDL_USEREVENT && received.user.code == 0x0B02) {
            break;
        }
    }
    if (received.type != SDL_USEREVENT || received.user.code != 0x0B02) {
        fprintf(stderr, "SDL event queue round trip failed\n");
        SDL_Quit();
        return 1;
    }

    SDL_Quit();
    puts("LBreakout2 SDL video/audio/timer/joystick init, software rendering, mixer open, and event path passed");
    return 0;
}
