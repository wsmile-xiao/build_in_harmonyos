/* Consumer test for the packaged SDL_image 1.2.12 (SDL 1.2 API).
 *
 * Only public API is used, so the test walks the real consumer path: the
 * packaged headers, the packaged library and its transitive codec
 * dependencies (libpng / libjpeg-turbo / libtiff / libwebp, via sdl12-compat
 * for the SDL 1.2 ABI).
 *
 * Checks performed (8 assertions):
 *   1. IMG_Linked_Version() agrees with the SDL_image.h version macros
 *   2. IMG_Init() enables the PNG/JPG/TIF/WEBP codecs
 *   3. IMG_isPNG() recognises a PNG stream
 *   4. IMG_Load_RW() decodes an embedded PNG   (external codec: libpng)
 *   5. the decoded PNG has the expected 3x2 geometry
 *   6. IMG_Load_RW() decodes an embedded BMP   (built-in codec path)
 *   7. the decoded BMP has the expected 3x2 geometry
 *   8. IMG_Load() on a missing file returns NULL (negative path)
 */
#include <limits.h>
#include <stdio.h>

#include <SDL/SDL.h>
#include <SDL/SDL_image.h>

#define EXPECTED_W 3
#define EXPECTED_H 2

static const unsigned char test_bmp[] = {
    0x42, 0x4d, 0x4e, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x36, 0x00,
    0x00, 0x00, 0x28, 0x00, 0x00, 0x00, 0x03, 0x00, 0x00, 0x00, 0x02, 0x00,
    0x00, 0x00, 0x01, 0x00, 0x18, 0x00, 0x00, 0x00, 0x00, 0x00, 0x18, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xff, 0xff, 0xff, 0x00, 0x00, 0x00,
    0xff, 0xff, 0xff, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xff, 0xff, 0xff,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
};
/* test_bmp: 78 bytes, 3x2 */
static const unsigned char test_png[] = {
    0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a, 0x00, 0x00, 0x00, 0x0d,
    0x49, 0x48, 0x44, 0x52, 0x00, 0x00, 0x00, 0x03, 0x00, 0x00, 0x00, 0x02,
    0x08, 0x02, 0x00, 0x00, 0x00, 0x12, 0x16, 0xf1, 0x4d, 0x00, 0x00, 0x00,
    0x13, 0x49, 0x44, 0x41, 0x54, 0x78, 0xda, 0x63, 0x60, 0x60, 0x60, 0xf8,
    0xff, 0xff, 0x3f, 0x03, 0x9c, 0x02, 0x92, 0x00, 0x4a, 0xc9, 0x08, 0xf8,
    0x66, 0x69, 0x9d, 0x68, 0x00, 0x00, 0x00, 0x00, 0x49, 0x45, 0x4e, 0x44,
    0xae, 0x42, 0x60, 0x82,
};
/* test_png: 76 bytes, 3x2 */
static int failures = 0;

static void check(int ok, const char *what)
{
    printf("%s %s\n", ok ? "ok  " : "FAIL", what);
    if (!ok) {
        failures++;
    }
}

static SDL_Surface *load_from_memory(const unsigned char *data, size_t size, const char *what)
{
    /* SDL 1.2 takes an int; the embedded fixtures are far below INT_MAX, so the
     * narrowing is explicit and checked here instead of silently at the call. */
    SDL_RWops *rw;
    SDL_Surface *surface;

    if (size > (size_t)INT_MAX) {
        printf("FAIL fixture too large for SDL_RWFromConstMem: %s\n", what);
        failures++;
        return NULL;
    }
    rw = SDL_RWFromConstMem(data, (int)size);

    if (rw == NULL) {
        printf("FAIL SDL_RWFromConstMem: %s\n", SDL_GetError());
        failures++;
        return NULL;
    }
    surface = IMG_Load_RW(rw, 1);
    if (surface == NULL) {
        printf("     IMG_GetError (%s): %s\n", what, IMG_GetError());
    }
    return surface;
}

int main(void)
{
    const SDL_version *linked;
    SDL_Surface *surface;
    SDL_RWops *rw;
    int flags;

    linked = IMG_Linked_Version();
    check(linked != NULL &&
              linked->major == SDL_IMAGE_MAJOR_VERSION &&
              linked->minor == SDL_IMAGE_MINOR_VERSION,
          "IMG_Linked_Version matches the SDL_image.h macros");

    /* SDL_Init(0) keeps the gate on the SDL_image codec path only: initialising
     * the video subsystem would make every codec assertion below unreachable on
     * a headless CI machine (no video driver -> SDL_Init(SDL_INIT_VIDEO) fails),
     * which would report a packaging failure for an unrelated reason. */
    if (SDL_Init(0) != 0) {
        printf("FAIL SDL_Init(0): %s\n", SDL_GetError());
        return 1;
    }

    flags = IMG_Init(IMG_INIT_PNG | IMG_INIT_JPG | IMG_INIT_TIF | IMG_INIT_WEBP);
    printf("     IMG_Init -> 0x%02x\n", flags);
    check((flags & IMG_INIT_PNG) && (flags & IMG_INIT_JPG) &&
              (flags & IMG_INIT_TIF) && (flags & IMG_INIT_WEBP),
          "IMG_Init enabled the PNG/JPG/TIF/WEBP codecs");

    /* format probing (separate RWops from the decoding below) */
    rw = SDL_RWFromConstMem(test_png, sizeof(test_png));
    check(rw != NULL && IMG_isPNG(rw) != 0, "IMG_isPNG recognises the PNG stream");
    if (rw != NULL) {
        SDL_RWclose(rw);
    }

    /* external codec path: libpng */
    surface = load_from_memory(test_png, sizeof(test_png), "png");
    check(surface != NULL, "IMG_Load_RW decodes PNG (libpng codec)");
    if (surface != NULL) {
        check(surface->w == EXPECTED_W && surface->h == EXPECTED_H,
              "decoded PNG has the expected 3x2 geometry");
        SDL_FreeSurface(surface);
    }

    /* built-in codec path */
    surface = load_from_memory(test_bmp, sizeof(test_bmp), "bmp");
    check(surface != NULL, "IMG_Load_RW decodes BMP (built-in codec)");
    if (surface != NULL) {
        check(surface->w == EXPECTED_W && surface->h == EXPECTED_H,
              "decoded BMP has the expected 3x2 geometry");
        SDL_FreeSurface(surface);
    }

    /* negative path: a file that does not exist must not yield a surface */
    surface = IMG_Load("/nonexistent/sdl-image-ohos/absent.png");
    check(surface == NULL, "IMG_Load fails cleanly on a missing file");
    if (surface != NULL) {
        SDL_FreeSurface(surface);
    }

    IMG_Quit();
    SDL_Quit();

    if (failures != 0) {
        printf("FAILED: %d check(s) did not pass\n", failures);
        return 1;
    }
    printf("ALL CHECKS PASSED\n");
    return 0;
}
