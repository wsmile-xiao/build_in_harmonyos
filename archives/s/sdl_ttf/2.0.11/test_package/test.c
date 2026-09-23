#include <SDL/SDL_ttf.h>
#include <stdio.h>

int main(void) {
    const SDL_version *version = TTF_Linked_Version();
    if (version == NULL || version->major != 2 || version->minor != 0 ||
        version->patch != 11) {
        fprintf(stderr, "unexpected SDL_ttf version\n");
        return 1;
    }
    if (TTF_Init() != 0 || TTF_WasInit() == 0) {
        fprintf(stderr, "TTF_Init/TTF_WasInit failed\n");
        return 1;
    }
    TTF_Quit();
    printf("SDL_ttf %d.%d.%d API checks passed\n", version->major,
           version->minor, version->patch);
    return 0;
}
