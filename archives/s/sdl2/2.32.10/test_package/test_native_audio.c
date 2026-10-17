#include <stdio.h>

#include <SDL.h>

#include "test_native_audio.h"

typedef struct AudioState
{
    SDL_atomic_t callbacks;
    SDL_atomic_t frames;
    SDL_atomic_t nonzero_samples;
    int channels;
    int phase;
} AudioState;

static void SDLCALL audio_callback(void *userdata, Uint8 *stream, int len)
{
    AudioState *state = (AudioState *)userdata;
    Sint16 *samples = (Sint16 *)stream;
    const int sample_count = len / (int)sizeof(*samples);
    int i;

    for (i = 0; i < sample_count; ++i) {
        samples[i] = state->phase ? 1800 : -1800;
        state->phase = !state->phase;
    }
    SDL_AtomicAdd(&state->callbacks, 1);
    SDL_AtomicAdd(&state->frames, sample_count / state->channels);
    SDL_AtomicAdd(&state->nonzero_samples, sample_count);
}

static int has_ohaudio_driver(void)
{
    int i;
    for (i = 0; i < SDL_GetNumAudioDrivers(); ++i) {
        const char *name = SDL_GetAudioDriver(i);
        if (name && SDL_strcmp(name, "ohaudio") == 0) {
            return 1;
        }
    }
    return 0;
}

int SDL2_RunNativeAudioProbe(void)
{
    AudioState state;
    SDL_AudioSpec wanted;
    SDL_AudioSpec obtained;
    SDL_AudioDeviceID device = 0;
    Uint64 deadline;
    int checks = 0;
    int rc = 1;

#define REQUIRE(expr, label)                                                   \
    do {                                                                       \
        if (!(expr)) {                                                         \
            fprintf(stderr, "SDL2_NATIVE_AUDIO_FAIL assertion=%s error=%s\n", \
                    label, SDL_GetError());                                    \
            goto cleanup;                                                      \
        }                                                                      \
        ++checks;                                                              \
    } while (0)

    SDL_zero(state);
    REQUIRE(SDL_setenv("SDL_AUDIODRIVER", "ohaudio", 1) == 0,
            "force_ohaudio");
    REQUIRE(has_ohaudio_driver(), "driver_registered");
    REQUIRE(SDL_Init(SDL_INIT_AUDIO) == 0, "audio_init");
    REQUIRE(SDL_GetCurrentAudioDriver() != NULL &&
                SDL_strcmp(SDL_GetCurrentAudioDriver(), "ohaudio") == 0,
            "driver_selected");

    SDL_zero(wanted);
    wanted.freq = 48000;
    wanted.format = AUDIO_S16LSB;
    wanted.channels = 2;
    wanted.samples = 512;
    wanted.callback = audio_callback;
    wanted.userdata = &state;
    state.channels = wanted.channels;
    device = SDL_OpenAudioDevice(NULL, 0, &wanted, &obtained,
                                 SDL_AUDIO_ALLOW_FREQUENCY_CHANGE |
                                     SDL_AUDIO_ALLOW_CHANNELS_CHANGE |
                                     SDL_AUDIO_ALLOW_SAMPLES_CHANGE);
    REQUIRE(device != 0, "open_output_device");
    REQUIRE(obtained.freq > 0 && obtained.channels >= 1 &&
                obtained.channels <= 2 && obtained.samples > 0 &&
                obtained.format == AUDIO_S16LSB,
            "negotiated_spec");
    state.channels = obtained.channels;

    SDL_PauseAudioDevice(device, 0);
    REQUIRE(SDL_GetAudioDeviceStatus(device) == SDL_AUDIO_PLAYING,
            "renderer_playing");
    deadline = SDL_GetTicks64() + 5000;
    while (SDL_AtomicGet(&state.callbacks) < 12 && SDL_GetTicks64() < deadline) {
        SDL_Delay(10);
    }
    REQUIRE(SDL_AtomicGet(&state.callbacks) >= 12, "callback_progress");
    REQUIRE(SDL_AtomicGet(&state.frames) > 0, "frame_progress");
    REQUIRE(SDL_AtomicGet(&state.nonzero_samples) > 0, "non_silent_samples");
    SDL_Delay(100);
    REQUIRE(SDL_GetAudioDeviceStatus(device) == SDL_AUDIO_PLAYING,
            "native_progress_stable");

    SDL_CloseAudioDevice(device);
    device = 0;
    SDL_QuitSubSystem(SDL_INIT_AUDIO);
    REQUIRE(SDL_WasInit(SDL_INIT_AUDIO) == 0, "audio_quit_clean");
    if (checks != 12) {
        fprintf(stderr, "SDL2_NATIVE_AUDIO_FAIL assertion_count=%d\n", checks);
        goto cleanup;
    }
    printf("SDL2_NATIVE_AUDIO_PASS assertions=%d callbacks=%d frames=%d "
           "nonzero_samples=%d driver=ohaudio\n",
           checks, SDL_AtomicGet(&state.callbacks),
           SDL_AtomicGet(&state.frames), SDL_AtomicGet(&state.nonzero_samples));
    rc = 0;

cleanup:
    if (device != 0) {
        SDL_CloseAudioDevice(device);
    }
    SDL_QuitSubSystem(SDL_INIT_AUDIO);
    return rc;
}

#ifndef SDL2_NATIVE_AUDIO_NO_MAIN
int main(void)
{
    return SDL2_RunNativeAudioProbe();
}
#endif
