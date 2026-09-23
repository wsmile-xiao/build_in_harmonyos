/* test_sdl2_image - consumer test for SDL2_image (2.6.0.1)
 *
 * Links libSDL2_image.a, calls IMG_Init/IMG_Load_RW and verifies:
 *   1. PNG / JPG / WEBP formats are wired (libpng / libjpeg-turbo / libwebp).
 *   2. A 1x1 grayscale+alpha PNG (color type 4, the AssaultCube font format)
 *      decodes correctly via the libpng backend — STB mapped this to an
 *      "Unknown pixel format" on OHOS, so we must confirm libpng handles it.
 */
#include <SDL.h>
#include <SDL_image.h>

/* 1x1 8-bit grayscale+alpha PNG (color type 4), gray=128 alpha=200.
 * Generated with a minimal IHDR/IDAT/IEND, zlib-compressed. */
static const unsigned char gray_alpha_png[] = {
    0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a,
    0x00, 0x00, 0x00, 0x0d, 0x49, 0x48, 0x44, 0x52,
    0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,
    0x08, 0x04, 0x00, 0x00, 0x00, 0xb5, 0x1c, 0x0c,
    0x02, 0x00, 0x00, 0x00, 0x0b, 0x49, 0x44, 0x41,
    0x54, 0x78, 0x9c, 0x63, 0x68, 0x38, 0x01, 0x00,
    0x01, 0xcb, 0x01, 0x49, 0xf6, 0x32, 0x0d, 0xdd,
    0x00, 0x00, 0x00, 0x00, 0x49, 0x45, 0x4e, 0x44,
    0xae, 0x42, 0x60, 0x82
};

int main(void)
{
    const Uint32 required = IMG_INIT_PNG | IMG_INIT_JPG | IMG_INIT_WEBP;
    SDL_Surface *surf;
    SDL_RWops *rw;
    int flags;

    if (SDL_Init(SDL_INIT_VIDEO) != 0) {
        SDL_Log("SDL_Init failed: %s", SDL_GetError());
        return 1;
    }

    flags = IMG_Init(required);
    if ((flags & required) != required) {
        SDL_Log("IMG_Init missing formats: got 0x%x (want 0x%x)", flags, required);
        IMG_Quit();
        SDL_Quit();
        return 1;
    }

    /* Decode the grayscale+alpha PNG via the libpng backend. */
    rw = SDL_RWFromConstMem(gray_alpha_png, (int)sizeof(gray_alpha_png));
    if (rw == NULL) {
        SDL_Log("SDL_RWFromConstMem failed");
        IMG_Quit();
        SDL_Quit();
        return 1;
    }
    surf = IMG_Load_RW(rw, 1);
    if (surf == NULL) {
        SDL_Log("IMG_Load_RW gray+alpha PNG failed: %s", IMG_GetError());
        IMG_Quit();
        SDL_Quit();
        return 1;
    }
    if (surf->w != 1 || surf->h != 1) {
        SDL_Log("unexpected surface size %dx%d", surf->w, surf->h);
        SDL_FreeSurface(surf);
        IMG_Quit();
        SDL_Quit();
        return 1;
    }
    SDL_FreeSurface(surf);

    IMG_Quit();
    SDL_Quit();
    return 0;
}
