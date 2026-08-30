/*
 * test.c — sdl-kitchensink 1.0.13 L1 consumer test.
 *
 * Exercises the real public API (R34/PF3): reports the library version,
 * verifies SDL pixel/audio format string helpers and the Kit_Init/Kit_Quit
 * lifecycle. No window/player is created (headless CI; SDL_VIDEODRIVER=dummy
 * is set by the test wrapper), so FFmpeg decoding is not exercised here —
 * decoding requires a real media file and a render target.
 */
#include <stdio.h>
#include <stdlib.h>

#include <kitchensink/kitchensink.h>
#include <SDL_audio.h> /* AUDIO_S16LSB - kitchensink.h does not pull SDL in */

int main(void) {
    Kit_Version ver;
    int ret = 0;

    Kit_GetVersion(&ver);
    printf("SDL_kitchensink version: %u.%u.%u\n", ver.major, ver.minor, ver.patch);
    if (ver.major != 1 || ver.minor != 0 || ver.patch != 13) {
        fprintf(stderr, "FAIL: unexpected version %u.%u.%u (expected 1.0.13)\n",
                ver.major, ver.minor, ver.patch);
        ret = 1;
    }

    /* Format helper round-trips (pure string functions, no init needed) */
    const char *pix = Kit_GetSDLPixelFormatString(SDL_PIXELFORMAT_RGB24);
    if (pix == NULL) {
        fprintf(stderr, "FAIL: Kit_GetSDLPixelFormatString returned NULL\n");
        ret = 1;
    } else {
        printf("SDL_PIXELFORMAT_RGB24 -> %s\n", pix);
    }
    const char *aud = Kit_GetSDLAudioFormatString(AUDIO_S16LSB);
    if (aud == NULL) {
        fprintf(stderr, "FAIL: Kit_GetSDLAudioFormatString returned NULL\n");
        ret = 1;
    } else {
        printf("AUDIO_S16LSB -> %s\n", aud);
    }

    /* Library init/quit lifecycle */
    if (Kit_Init(0) != 0) {
        fprintf(stderr, "FAIL: Kit_Init failed: %s\n", Kit_GetError());
        return 1;
    }
    Kit_Quit();

    if (ret == 0) {
        printf("test sdl-kitchensink 1.0.13: OK\n");
    }
    return ret;
}
