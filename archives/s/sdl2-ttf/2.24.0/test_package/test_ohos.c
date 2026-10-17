/* test_ohos.c - HarmonyOS-specific platform-adaptation test for SDL2_ttf
 *
 * Verifies the OHOS platform adaptation actually took effect at runtime:
 *  - SDL video subsystem initializes on HarmonyOS (SDL_GetCurrentVideoDriver)
 *  - SDL2_ttf uses the EXTERNAL FreeType/HarfBuzz provided by the conan
 *    dependencies (--disable-freetype-builtin --disable-harfbuzz-builtin).
 *    SDL2_ttf 2.24.0 bundled submodules would report FreeType 2.13.x /
 *    HarfBuzz 8.x; the external linkage must report FreeType >= 2.14 and
 *    HarfBuzz >= 14, proving the OHOS adaptation (system deps instead of the
 *    tarball's absent external/ submodules) is active.
 *
 * Requires sdl2/2.30.10, freetype/2.14.3, harfbuzz/14.2.0.1.1.2.
 */
#include <SDL.h>
#include <SDL_ttf.h>
#include <stdio.h>

int main(void)
{
    const char *driver = NULL;
    int ft_major = 0, ft_minor = 0, ft_patch = 0;
    int hb_major = 0, hb_minor = 0, hb_patch = 0;

    if (SDL_Init(SDL_INIT_VIDEO) != 0) {
        fprintf(stderr, "SDL_Init failed: %s\n", SDL_GetError());
        return 1;
    }

    /* OHOS platform: an actual video driver must be active (dummy or native) */
    driver = SDL_GetCurrentVideoDriver();
    if (driver == NULL || driver[0] == '\0') {
        fprintf(stderr, "SDL_GetCurrentVideoDriver returned NULL on OHOS\n");
        SDL_Quit();
        return 1;
    }
    printf("OHOS video driver: %s\n", driver);

    if (TTF_Init() != 0) {
        fprintf(stderr, "TTF_Init failed: %s\n", TTF_GetError());
        SDL_Quit();
        return 1;
    }

    /* Platform adaptation: external (non-builtin) FreeType must be linked */
    TTF_GetFreeTypeVersion(&ft_major, &ft_minor, &ft_patch);
    printf("External FreeType version: %d.%d.%d\n", ft_major, ft_minor, ft_patch);
    if (ft_major < 2 || (ft_major == 2 && ft_minor < 14)) {
        fprintf(stderr, "expected external FreeType >= 2.14, got %d.%d.%d "
                "(builtin fallback would break OHOS external-dep adaptation)\n",
                ft_major, ft_minor, ft_patch);
        TTF_Quit();
        SDL_Quit();
        return 1;
    }

    /* Platform adaptation: external (non-builtin) HarfBuzz must be linked */
    TTF_GetHarfBuzzVersion(&hb_major, &hb_minor, &hb_patch);
    printf("External HarfBuzz version: %d.%d.%d\n", hb_major, hb_minor, hb_patch);
    if (hb_major < 14) {
        fprintf(stderr, "expected external HarfBuzz >= 14, got %d.%d.%d "
                "(builtin fallback would break OHOS external-dep adaptation)\n",
                hb_major, hb_minor, hb_patch);
        TTF_Quit();
        SDL_Quit();
        return 1;
    }

    TTF_Quit();
    SDL_Quit();
    printf("SDL2_ttf OHOS platform-adaptation test: OK\n");
    return 0;
}
