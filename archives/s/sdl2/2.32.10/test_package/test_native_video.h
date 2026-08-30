#ifndef SDL2_TEST_NATIVE_VIDEO_H_
#define SDL2_TEST_NATIVE_VIDEO_H_

#include <SDL_stdinc.h>

typedef int (*SDL2_NativeVideoPresentationObserver)(
    void *userdata, Uint8 red, Uint8 green, Uint8 blue, Uint8 alpha);

int SDL2_RunNativeVideoProbe(Uint64 surface_id, int width, int height);
int SDL2_RunNativeVideoProbeWithObserver(
    Uint64 surface_id, int width, int height,
    SDL2_NativeVideoPresentationObserver observer, void *observer_userdata);

#endif
