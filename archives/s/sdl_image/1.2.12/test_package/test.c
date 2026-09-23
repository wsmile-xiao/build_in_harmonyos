#include <SDL/SDL_image.h>
#include <stdio.h>

int main(void) {
    const SDL_version *version = IMG_Linked_Version();
    if (version == NULL || version->major != 1 || version->minor != 2 ||
        version->patch != 12) {
        fprintf(stderr, "unexpected SDL_image version\n");
        return 1;
    }
    if (IMG_Init(0) != 0) {
        fprintf(stderr, "IMG_Init(0) returned an unexpected flag\n");
        return 1;
    }
    IMG_Quit();
    printf("SDL_image %d.%d.%d API checks passed\n", version->major,
           version->minor, version->patch);
    return 0;
}
