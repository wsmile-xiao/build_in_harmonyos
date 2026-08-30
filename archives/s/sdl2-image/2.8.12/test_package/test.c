/* test_sdl2_image - consumer test for SDL2_image
 *
 * Links libSDL2_image.a, calls IMG_Init/IMG_Load_RW and loads a tiny in-memory
 * BMP to exercise the real image-loading code path (STB backend).
 */
#include <SDL.h>
#include <SDL_image.h>

/* Minimal 1x1 24-bit BMP (yellow pixel); pixel row padded to 4 bytes */
static const unsigned char tiny_bmp[] = {
    0x42, 0x4d, 0x7a, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x36, 0x00, 0x00, 0x00, 0x28, 0x00, 0x00, 0x00, 0x01, 0x00,
    0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01, 0x00, 0x18, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x04, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0xff, 0xff, 0x00
};

int main(void)
{
    SDL_Surface *surf;
    SDL_RWops *rw;
    int flags;

    if (SDL_Init(SDL_INIT_VIDEO) != 0) {
        SDL_Log("SDL_Init failed: %s", SDL_GetError());
        return 1;
    }

    flags = IMG_Init(IMG_INIT_PNG | IMG_INIT_JPG | IMG_INIT_TIF | IMG_INIT_WEBP);
    if ((flags & (IMG_INIT_PNG | IMG_INIT_JPG | IMG_INIT_TIF | IMG_INIT_WEBP)) !=
        (IMG_INIT_PNG | IMG_INIT_JPG | IMG_INIT_TIF | IMG_INIT_WEBP)) {
        SDL_Log("IMG_Init missing formats: got 0x%x", flags);
        IMG_Quit();
        SDL_Quit();
        return 1;
    }

    rw = SDL_RWFromConstMem(tiny_bmp, (int)sizeof(tiny_bmp));
    if (rw == NULL) {
        SDL_Log("SDL_RWFromConstMem failed");
        IMG_Quit();
        SDL_Quit();
        return 1;
    }
    surf = IMG_Load_RW(rw, 1);
    if (surf == NULL) {
        SDL_Log("IMG_Load_RW failed: %s", IMG_GetError());
        IMG_Quit();
        SDL_Quit();
        return 1;
    }
    SDL_FreeSurface(surf);
    IMG_Quit();
    SDL_Quit();
    return 0;
}
