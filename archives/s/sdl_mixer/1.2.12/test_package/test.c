#include <SDL/SDL_mixer.h>
#include <stdio.h>

int main(void) {
    const SDL_version *version = Mix_Linked_Version();
    if (version == NULL || version->major != 1 || version->minor != 2 ||
        version->patch != 12) {
        fprintf(stderr, "unexpected SDL_mixer version\n");
        return 1;
    }
    if (Mix_Init(0) != 0) {
        fprintf(stderr, "Mix_Init(0) returned an unexpected flag\n");
        return 1;
    }
    Mix_Quit();
    printf("SDL_mixer %d.%d.%d API checks passed\n", version->major,
           version->minor, version->patch);
    return 0;
}
