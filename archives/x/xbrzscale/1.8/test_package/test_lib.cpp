// test_lib.cpp — xbrzscale consumer test: really exercises libxbrzscale (R34).
//
// Builds small in-memory ARGB surfaces, runs libxbrzscale::scale at
// several factors and verifies output dimensions, non-trivial pixels and
// the surface<->uint32 roundtrip. Prints ok/not-ok lines and exits 0 only
// when all 6 assertions hold (the test_package driver counts this program
// as one end-to-end case via its exit code).
#include <cstdint>
#include <cstdio>

#if __has_include(<SDL2/SDL.h>)
#include <SDL2/SDL.h>
#else
#include <SDL.h>
#endif

#include "libxbrzscale.h"

static int failures = 0;
static int current = 0;

static void check(bool cond, const char *desc) {
    ++current;
    if (cond) {
        std::printf("ok %d - %s\n", current, desc);
    } else {
        std::printf("not ok %d - %s\n", current, desc);
        ++failures;
    }
}

static SDL_Surface *make_input(int w, int h) {
    SDL_Surface *s = libxbrzscale::createARGBSurface(w, h);
    if (!s) {
        return NULL;
    }
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            Uint8 r = (Uint8)((x * 64) & 0xff);
            Uint8 g = (Uint8)((y * 64) & 0xff);
            Uint8 b = (Uint8)(((x + y) * 32) & 0xff);
            Uint32 c = SDL_MapRGBA(s->format, r, g, b, 0xff);
            libxbrzscale::SDL_PutPixel(s, x, y, c);
        }
    }
    return s;
}

static bool surface_has_nonzero_pixels(SDL_Surface *s) {
    for (int y = 0; y < s->h; ++y) {
        for (int x = 0; x < s->w; ++x) {
            if (libxbrzscale::SDL_GetPixel(s, x, y) != 0) {
                return true;
            }
        }
    }
    return false;
}

int main() {
    if (SDL_Init(0) != 0) {
        std::fprintf(stderr, "SDL_Init failed: %s\n", SDL_GetError());
        return 1;
    }

    SDL_Surface *in4 = make_input(4, 4);
    check(in4 != NULL && in4->w == 4 && in4->h == 4, "createARGBSurface builds a 4x4 surface");

    SDL_Surface *out2 = in4 ? libxbrzscale::scale(in4, 2) : NULL;
    check(out2 != NULL && out2->w == 8 && out2->h == 8, "scale(factor=2) yields an 8x8 surface");
    check(out2 != NULL && surface_has_nonzero_pixels(out2), "scale(factor=2) output carries image data");

    SDL_Surface *in4b = make_input(4, 4);
    SDL_Surface *out3 = in4b ? libxbrzscale::scale(in4b, 3) : NULL;
    check(out3 != NULL && out3->w == 12 && out3->h == 12, "scale(factor=3) yields a 12x12 surface");

    SDL_Surface *tiny = make_input(2, 2);
    bool roundtrip = false;
    if (tiny) {
        uint32_t *buf = libxbrzscale::surfaceToUint32(tiny);
        SDL_Surface *back = libxbrzscale::createARGBSurface(2, 2);
        if (buf && back) {
            libxbrzscale::uint32toSurface(buf, back);
            roundtrip = true;
            for (int y = 0; y < 2 && roundtrip; ++y) {
                for (int x = 0; x < 2 && roundtrip; ++x) {
                    if (libxbrzscale::SDL_GetPixel(tiny, x, y) != libxbrzscale::SDL_GetPixel(back, x, y)) {
                        roundtrip = false;
                    }
                }
            }
        }
        delete[] buf;
        if (back) {
            SDL_FreeSurface(back);
        }
        SDL_FreeSurface(tiny);
    }
    check(roundtrip, "surfaceToUint32/uint32toSurface roundtrip preserves pixels");

    SDL_Surface *in4c = make_input(4, 4);
    SDL_Surface *out4 = in4c ? libxbrzscale::scale(in4c, 4) : NULL;
    check(out4 != NULL && out4->w == 16 && out4->h == 16, "scale(factor=4) yields a 16x16 surface");

    if (out2) {
        SDL_FreeSurface(out2);
    }
    if (out3) {
        SDL_FreeSurface(out3);
    }
    if (out4) {
        SDL_FreeSurface(out4);
    }
    SDL_Quit();
    std::printf("# %d/%d lib assertions passed\n", current - failures, current);
    return failures == 0 ? 0 : 1;
}
