#include <stdio.h>
#include <SDL3/SDL.h>

int main(void) {
    /* Runtime version reported by the shared library must match the
     * headers we compiled against. SDL3 expresses versions as a single
     * integer (major*1000000 + minor*1000 + patch). */
    int compiled = SDL_VERSION;
    int runtime = SDL_GetVersion();

    printf("SDL3 compiled: %d.%d.%d, runtime: %d.%d.%d, platform: %s\n",
           SDL_VERSIONNUM_MAJOR(compiled), SDL_VERSIONNUM_MINOR(compiled),
           SDL_VERSIONNUM_MICRO(compiled),
           SDL_VERSIONNUM_MAJOR(runtime), SDL_VERSIONNUM_MINOR(runtime),
           SDL_VERSIONNUM_MICRO(runtime), SDL_GetPlatform());

    if (runtime != compiled) {
        fprintf(stderr, "FAIL: runtime SDL version mismatch\n");
        return 1;
    }

    /* Real subsystem init/quit cycle (EVENTS needs no display, safe on
     * headless CI workers). */
    if (!SDL_InitSubSystem(SDL_INIT_EVENTS)) {
        fprintf(stderr, "FAIL: SDL_InitSubSystem(EVENTS): %s\n", SDL_GetError());
        return 1;
    }
    SDL_QuitSubSystem(SDL_INIT_EVENTS);
    SDL_Quit();

    printf("test sdl3 3.4.8: OK\n");
    return 0;
}
