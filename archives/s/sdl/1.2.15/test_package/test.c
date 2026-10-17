/* Consumer test for sdl/1.2.15 (headless).
 *
 * Drives the packaged SDL 1.2 library end to end without a display:
 *   SDL_Init(VIDEO|TIMER)  ->  select the dummy video driver
 *   ->  SDL_SetVideoMode   ->  SDL_FillRect / SDL_MapRGB
 *   ->  SDL_Flip           ->  SDL_GetTicks       ->  SDL_Quit
 * The dummy driver is compiled in and is the documented headless path
 * (SDL_VIDEODRIVER=dummy), so this exercises the real video subsystem,
 * surface blitting and the timer subsystem.
 */
#include <stdio.h>
#include <string.h>

#include "SDL.h"

#define CHECK(cond, msg)                                             \
    do {                                                             \
        if (!(cond)) {                                               \
            fprintf(stderr, "FAIL: %s (line %d)\n", msg, __LINE__);   \
            return 1;                                                \
        }                                                            \
    } while (0)

int main(int argc, char **argv)
{
    SDL_Surface *screen = NULL;
    SDL_Surface *tmp = NULL;
    SDL_Rect rect;
    Uint32 start, elapsed;
    char drv_name[64];
    int i;

    (void)argc;
    (void)argv;

    /* 1) Version string from the linked library. */
    {
        const SDL_version *v = SDL_Linked_Version();
        CHECK(v != NULL, "SDL_Linked_Version returned NULL");
        printf("SDL linked version: %d.%d.%d\n", v->major, v->minor, v->patch);
        CHECK(v->major == 1 && v->minor == 2, "unexpected SDL major/minor");
    }

    /* 2) Init video + timer through the dummy driver (headless). */
    if (SDL_getenv("SDL_VIDEODRIVER") == NULL)
        SDL_putenv("SDL_VIDEODRIVER=dummy");
    CHECK(SDL_Init(SDL_INIT_VIDEO | SDL_INIT_TIMER) == 0,
          "SDL_Init failed");
    SDL_WM_SetCaption("sdl-consumer", NULL);
    {
        const char *drv = SDL_VideoDriverName(drv_name, sizeof(drv_name));
        CHECK(drv != NULL, "SDL_VideoDriverName returned NULL");
        printf("SDL video driver: %s\n", drv);
    }

    /* 3) Surface creation, pixel mapping and a real blit. */
    screen = SDL_SetVideoMode(160, 120, 32, SDL_SWSURFACE);
    CHECK(screen != NULL, "SDL_SetVideoMode failed");
    SDL_FillRect(screen, NULL, SDL_MapRGB(screen->format, 0x20, 0x40, 0x60));

    tmp = SDL_CreateRGBSurface(SDL_SWSURFACE, 32, 32, 32,
                               screen->format->Rmask, screen->format->Gmask,
                               screen->format->Bmask, screen->format->Amask);
    CHECK(tmp != NULL, "SDL_CreateRGBSurface failed");
    SDL_FillRect(tmp, NULL, SDL_MapRGB(tmp->format, 0xFF, 0x00, 0x00));
    rect.x = 16; rect.y = 16; rect.w = 32; rect.h = 32;
    CHECK(SDL_BlitSurface(tmp, NULL, screen, &rect) == 0,
          "SDL_BlitSurface failed");
    CHECK(SDL_Flip(screen) == 0, "SDL_Flip failed");

    /* 4) Timer subsystem: SDL_Delay/SDL_GetTicks must advance. */
    start = SDL_GetTicks();
    for (i = 0; i < 5; i++)
        SDL_Delay(4);
    elapsed = SDL_GetTicks();
    CHECK(elapsed >= start, "timer went backwards");
    printf("SDL_GetTicks advanced by %u ms\n", (unsigned)(elapsed - start));

    SDL_FreeSurface(tmp);
    SDL_FreeSurface(screen);
    SDL_Quit();
    printf("SDL-CONSUMER-OK\n");
    return 0;
}
