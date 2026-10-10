/* test_sdl_gfx.c — consumer-side (L1) verification for the sdl_gfx Conan package.
 *
 * Exercises the four upstream components through the packaged headers+library:
 *   SDL_gfxPrimitives.h  -> filledCircleColor / lineColor (pixel-level assertions)
 *   SDL_rotozoom.h       -> zoomSurface / rotozoomSurface
 *   SDL_framerate.h      -> SDL_initFramerate / SDL_setFramerate / SDL_getFramerate
 *   SDL_imageFilter.h    -> SDL_imageFilterShiftLeft (the C path used on aarch64)
 *
 * NOTE (SDL_gfx 2.0.7 API convention, SDL_gfxPrimitives.h line 44):
 *   all `___Color` routines take the color as 0xRRGGBBAA — the **alpha byte is the
 *   low byte**.  alpha = 0x00 means "fully transparent" and the call silently draws
 *   nothing, which is why the assertions below use ...FF-suffixed colors.
 *
 * Exit code 0 = all assertions passed, 1 = at least one failed.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <SDL/SDL.h>
#include <SDL_gfxPrimitives.h>
#include <SDL_rotozoom.h>
#include <SDL_framerate.h>
#include <SDL_imageFilter.h>

#define OPAQUE_RED   0xFF0000FFu  /* R=FF G=00 B=00 A=FF */
#define OPAQUE_GREEN 0x00FF00FFu  /* R=00 G=FF B=00 A=FF */
#define OPAQUE_BLUE  0x0000FFFFu  /* R=00 G=00 B=FF A=FF */
#define TRANSPARENT  0x0000FF00u  /* R=00 G=00 B=FF A=00 -> must not draw */

static int g_pass = 0;
static int g_fail = 0;

static void check(int cond, const char *what)
{
    if (cond) {
        g_pass++;
        printf("PASS  %s\n", what);
    } else {
        g_fail++;
        printf("FAIL  %s\n", what);
    }
}

int main(void)
{
    SDL_Surface *surface = NULL;
    SDL_Surface *zoomed = NULL;
    SDL_Surface *rotated = NULL;
    Uint32 *pixels;
    int pitch32;
    FPSmanager fps;
    char driver[32] = {0};
    unsigned char src[8] = {0, 1, 2, 3, 4, 5, 6, 7};
    unsigned char dst[8] = {0, 0, 0, 0, 0, 0, 0, 0};
    const SDL_version *v;

    if (SDL_Init(SDL_INIT_VIDEO) != 0) {
        /* Headless sandbox: fall back to the "no subsystem" init — the assertions
         * below only need software surfaces. */
        printf("INFO  SDL_Init(SDL_INIT_VIDEO) failed (%s), retrying with SDL_Init(0)\n",
               SDL_GetError());
        if (SDL_Init(0) != 0) {
            printf("FAIL  SDL_Init(0): %s\n", SDL_GetError());
            return 1;
        }
    }
    SDL_VideoDriverName(driver, sizeof(driver));
    v = SDL_Linked_Version();
    printf("INFO  SDL %d.%d.%d, video driver: %s\n", v->major, v->minor, v->patch, driver);

    surface = SDL_CreateRGBSurface(SDL_SWSURFACE, 32, 32, 32,
                                   0x00FF0000u, 0x0000FF00u, 0x000000FFu, 0xFF000000u);
    check(surface != NULL, "SDL_CreateRGBSurface(32x32x32, ARGB)");
    if (surface == NULL) {
        SDL_Quit();
        return 1;
    }

    SDL_FillRect(surface, NULL, SDL_MapRGB(surface->format, 0, 0, 0));
    pixels = (Uint32 *)surface->pixels;
    pitch32 = surface->pitch / 4;
    check(pixels[0] == 0xFF000000u, "SDL_FillRect() fills opaque black");

    /* ---- SDL_gfxPrimitives ---- */
    check(filledCircleColor(surface, 16, 16, 8, OPAQUE_RED) >= 0,
          "filledCircleColor() succeeds");
    check(pixels[16 * pitch32 + 16] == 0xFFFF0000u,
          "filledCircleColor() centre pixel is opaque red");
    check(pixels[16 * pitch32 + 23] == 0xFFFF0000u,
          "filledCircleColor() boundary pixel is opaque red");
    check(pixels[0] == 0xFF000000u,
          "filledCircleColor() left (0,0) background untouched");

    check(lineColor(surface, 0, 0, 31, 31, OPAQUE_GREEN) >= 0,
          "lineColor() succeeds");
    check(pixels[0] == 0xFF00FF00u, "lineColor() sets the start pixel to opaque green");
    check(pixels[31 * pitch32 + 31] == 0xFF00FF00u,
          "lineColor() sets the end pixel to opaque green");

    /* box placed away from the diagonal/ellipse: (25..29, 4..8).
       Per the 0xRRGGBBAA convention: alpha=00 draws nothing, alpha=FF is opaque,
       and the lower-right edge (x2,y2) is exclusive. */
    check(boxColor(surface, 25, 4, 29, 8, TRANSPARENT) >= 0,
          "boxColor(alpha=00) is a documented no-op");
    check(pixels[6 * pitch32 + 27] == 0xFF000000u,
          "boxColor(alpha=00) left the background unchanged");
    check(boxColor(surface, 25, 4, 29, 8, OPAQUE_BLUE) >= 0,
          "boxColor(alpha=FF) succeeds");
    check(pixels[6 * pitch32 + 27] == 0xFF0000FFu,
          "boxColor(alpha=FF) fills the box with opaque blue");
    check(pixels[8 * pitch32 + 29] == 0xFF000000u,
          "boxColor() lower-right edge is exclusive");

    /* ---- SDL_rotozoom ---- */
    zoomed = zoomSurface(surface, 2.0, 2.0, 0);
    check(zoomed != NULL && zoomed->w == 64 && zoomed->h == 64,
          "zoomSurface(2.0) doubles the surface size");
    if (zoomed != NULL)
        SDL_FreeSurface(zoomed);

    rotated = rotozoomSurface(surface, 45.0, 1.0, 1);
    check(rotated != NULL && rotated->w > 0 && rotated->h > 0,
          "rotozoomSurface(45 deg) returns a surface");
    if (rotated != NULL)
        SDL_FreeSurface(rotated);

    /* ---- SDL_framerate ---- */
    SDL_initFramerate(&fps);
    check(SDL_setFramerate(&fps, 30) >= 0, "SDL_setFramerate(30) succeeds");
    check(SDL_getFramerate(&fps) == 30, "SDL_getFramerate() returns 30");

    /* ---- SDL_imageFilter (C implementation used on aarch64) ---- */
    check(SDL_imageFilterShiftLeft(src, dst, 8, 1) >= 0,
          "SDL_imageFilterShiftLeft() succeeds");
    check(dst[1] == 2 && dst[7] == 14,
          "SDL_imageFilterShiftLeft(S<<1) values are {0,2,4,6,8,10,12,14}");

    SDL_FreeSurface(surface);
    SDL_Quit();

    printf("RESULT %d passed, %d failed\n", g_pass, g_fail);
    return g_fail == 0 ? 0 : 1;
}
