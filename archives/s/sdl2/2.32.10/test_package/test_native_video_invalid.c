#include <stdio.h>

#include <SDL.h>

typedef struct InvalidTupleCase
{
    const char *name;
    const char *surface_id;
    const char *width;
    const char *height;
    const char *error_fragment;
} InvalidTupleCase;

static int run_case(const InvalidTupleCase *test_case)
{
    int init_result;
    const char *error;

    SDL_ResetHint(SDL_HINT_NATIVEWINDOW_SURFACE_ID);
    SDL_ResetHint(SDL_HINT_NATIVEWINDOW_WIDTH);
    SDL_ResetHint(SDL_HINT_NATIVEWINDOW_HEIGHT);
    if (test_case->surface_id) {
        SDL_SetHint(SDL_HINT_NATIVEWINDOW_SURFACE_ID, test_case->surface_id);
    }
    if (test_case->width) {
        SDL_SetHint(SDL_HINT_NATIVEWINDOW_WIDTH, test_case->width);
    }
    if (test_case->height) {
        SDL_SetHint(SDL_HINT_NATIVEWINDOW_HEIGHT, test_case->height);
    }

    SDL_ClearError();
    init_result = SDL_InitSubSystem(SDL_INIT_VIDEO);
    error = SDL_GetError();
    if (init_result == 0) {
        fprintf(stderr,
                "SDL2_NATIVE_VIDEO_INVALID_FAIL case=%s unexpectedly_initialized\n",
                test_case->name);
        SDL_QuitSubSystem(SDL_INIT_VIDEO);
        return 0;
    }
    if (!error || !SDL_strstr(error, test_case->error_fragment)) {
        fprintf(stderr,
                "SDL2_NATIVE_VIDEO_INVALID_FAIL case=%s error=%s expected=%s\n",
                test_case->name, error ? error : "", test_case->error_fragment);
        SDL_QuitSubSystem(SDL_INIT_VIDEO);
        return 0;
    }
    SDL_QuitSubSystem(SDL_INIT_VIDEO);
    return 1;
}

int main(void)
{
    static const InvalidTupleCase cases[] = {
        {"surface_missing", NULL, "640", "480", "surface ID"},
        {"surface_zero", "0", "640", "480", "surface ID"},
        {"surface_plus", "+1", "640", "480", "surface ID"},
        {"surface_minus", "-1", "640", "480", "surface ID"},
        {"surface_space", " 1", "640", "480", "surface ID"},
        {"surface_tail", "1x", "640", "480", "surface ID"},
        {"surface_overflow", "18446744073709551616", "640", "480", "surface ID"},
        {"width_missing", "1", NULL, "480", "width"},
        {"width_zero", "1", "0", "480", "width"},
        {"width_plus", "1", "+1", "480", "width"},
        {"width_overflow", "1", "2147483648", "480", "width"},
        {"height_missing", "1", "640", NULL, "height"},
        {"height_minus", "1", "640", "-1", "height"},
        {"height_overflow", "1", "640", "2147483648", "height"},
    };
    int passed = 0;
    size_t i;

    if (SDL_setenv("SDL_VIDEODRIVER", "nativewindow", 1) != 0) {
        fprintf(stderr, "SDL2_NATIVE_VIDEO_INVALID_FAIL setenv=%s\n",
                SDL_GetError());
        return 1;
    }
    for (i = 0; i < SDL_arraysize(cases); ++i) {
        if (!run_case(&cases[i])) {
            return 1;
        }
        ++passed;
    }
    printf("SDL2_NATIVE_VIDEO_INVALID_PASS cases=%d\n", passed);
    return passed == (int)SDL_arraysize(cases) ? 0 : 1;
}
