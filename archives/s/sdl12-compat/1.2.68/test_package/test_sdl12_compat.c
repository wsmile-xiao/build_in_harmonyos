#include <SDL.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>

static int package_sdl2_is_loaded(void)
{
    const char *expected = getenv("EXPECTED_SDL2_PATH");
    const char *package_relative;
    struct stat expected_stat;
    FILE *maps;
    char line[2048];

    if (expected == NULL || expected[0] != '/' || stat(expected, &expected_stat) != 0) {
        return 0;
    }
    package_relative = strstr(expected, "/p/b/");
    if (package_relative == NULL) {
        return 0;
    }
    maps = fopen("/proc/self/maps", "r");
    if (maps == NULL) {
        return 0;
    }
    while (fgets(line, sizeof(line), maps) != NULL) {
        char mapped_path[2048] = {0};

        if (sscanf(line, "%*s %*s %*s %*s %*s %2047s", mapped_path) == 1) {
            size_t mapped_length = strlen(mapped_path);
            size_t expected_length = strlen(package_relative);

            if (mapped_length >= expected_length &&
                    strcmp(mapped_path + mapped_length - expected_length,
                           package_relative) == 0) {
                fclose(maps);
                return 1;
            }
        }
    }
    fclose(maps);
    return 0;
}

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
    Uint32 started;

    if (SDL_Init(SDL_INIT_VIDEO | SDL_INIT_TIMER) != 0) {
        return fail("SDL_Init");
    }
    if (SDL_Linked_Version()->major != 1 || SDL_Linked_Version()->minor != 2) {
        fprintf(stderr, "unexpected SDL compatibility version: %u.%u.%u\n",
                SDL_Linked_Version()->major, SDL_Linked_Version()->minor,
                SDL_Linked_Version()->patch);
        SDL_Quit();
        return 1;
    }
    if (!package_sdl2_is_loaded()) {
        fprintf(stderr, "packaged libSDL2-2.0.so.0 is not loaded\n");
        SDL_Quit();
        return 1;
    }

    screen = SDL_SetVideoMode(64, 48, 32, SDL_SWSURFACE);
    if (screen == NULL) {
        return fail("SDL_SetVideoMode");
    }
    color = SDL_MapRGB(screen->format, 12, 34, 56);
    if (SDL_FillRect(screen, NULL, color) != 0) {
        return fail("SDL_FillRect");
    }
    if (SDL_Flip(screen) != 0) {
        return fail("SDL_Flip");
    }

    pushed.type = SDL_USEREVENT;
    pushed.user.code = 0x1268;
    /* sdl12-compat returns 0 on success and a negative value on failure. */
    if (SDL_PushEvent(&pushed) < 0) {
        return fail("SDL_PushEvent");
    }
    while (SDL_PollEvent(&received) == 1) {
        if (received.type == SDL_USEREVENT && received.user.code == 0x1268) {
            break;
        }
    }
    if (received.type != SDL_USEREVENT || received.user.code != 0x1268) {
        fprintf(stderr, "SDL 1.2 event queue round trip failed\n");
        SDL_Quit();
        return 1;
    }

    started = SDL_GetTicks();
    SDL_Delay(5);
    if (SDL_GetTicks() < started) {
        fprintf(stderr, "SDL timer moved backwards\n");
        SDL_Quit();
        return 1;
    }

    printf("sdl12-compat consumer test passed\n");
    SDL_Quit();
    return 0;
}
