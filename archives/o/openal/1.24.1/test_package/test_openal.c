/*
 * OpenAL Soft 1.24.1 consumer test for OpenHarmony (aarch64).
 *
 * End-to-end consumer workflow against the packaged static libopenal:
 *   A) null backend  — open the default device with ALSOFT_DRIVERS=null, build a
 *                      context, upload PCM, drive a source, and exercise the
 *                      error-return path.
 *   B) loopback backend — open a real ALC_SOFT_loopback device at 8 kHz mono,
 *                      render samples with alcRenderSamplesSOFT() and verify the
 *                      mixer actually produced the expected 220 Hz waveform
 *                      (peak amplitude + zero-crossing rate), not silence.
 *
 * No audio hardware is required: both backends are built into the library.
 */
#include <AL/al.h>
#include <AL/alc.h>

/* alext.h only declares the extension *function* prototypes when this is set
 * (the ALC_SOFT_loopback enums are unconditional, the prototypes are not). */
#define AL_ALEXT_PROTOTYPES 1
#include <AL/alext.h>   /* alcLoopbackOpenDeviceSOFT / alcRenderSamplesSOFT */

#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define SAMPLE_RATE 8000
#define TONE_HZ 220
#define TONE_SAMPLES 960
#define FULL_TONE_SAMPLES 8000

static int g_checks;
static int g_failures;

static void check(int ok, const char *what)
{
    g_checks++;
    if (ok) {
        printf("PASS: %s\n", what);
    } else {
        g_failures++;
        printf("FAIL: %s\n", what);
    }
}

/* Fill `out` with a mono 16-bit sine wave of TONE_HZ at SAMPLE_RATE. */
static void fill_tone(short *out, int count)
{
    int i;
    for (i = 0; i < count; i++) {
        const double t = (double)i / (double)SAMPLE_RATE;
        out[i] = (short)lround(0.5 * 32767.0 * sin(2.0 * M_PI * TONE_HZ * t));
    }
}

static int count_zero_crossings(const short *samples, int count)
{
    int i, crossings = 0;
    for (i = 1; i < count; i++) {
        if ((samples[i - 1] < 0 && samples[i] >= 0) ||
            (samples[i - 1] >= 0 && samples[i] < 0)) {
            crossings++;
        }
    }
    return crossings;
}

static int peak_amplitude(const short *samples, int count)
{
    int i, peak = 0;
    for (i = 0; i < count; i++) {
        const int mag = samples[i] < 0 ? -(int)samples[i] : (int)samples[i];
        if (mag > peak) {
            peak = mag;
        }
    }
    return peak;
}

/* ── A) null backend ─────────────────────────────────────────────────────── */
static int run_null_backend(void)
{
    static const short samples[8] = {0, 512, -512, 1024, -1024, 256, -256, 0};
    ALCdevice *device = NULL;
    ALCcontext *context = NULL;
    const ALchar *version, *vendor, *renderer;
    ALuint buffer = 0, source = 0;
    ALint state = 0;

    check(setenv("ALSOFT_DRIVERS", "null", 1) == 0,
          "ALSOFT_DRIVERS=null exported");

    device = alcOpenDevice(NULL);
    check(device != NULL, "A.null alcOpenDevice(NULL) returns a device");
    if (!device) {
        return 1;
    }
    check(alcGetString(device, ALC_DEVICE_SPECIFIER) != NULL,
          "A.null alcGetString(ALC_DEVICE_SPECIFIER) is non-NULL");

    context = alcCreateContext(device, NULL);
    check(context != NULL, "A.null alcCreateContext() returns a context");
    if (!context) {
        alcCloseDevice(device);
        return 1;
    }
    check(alcMakeContextCurrent(context) == ALC_TRUE,
          "A.null alcMakeContextCurrent() succeeds");
    check(alGetError() == AL_NO_ERROR, "A.null alGetError() is AL_NO_ERROR after setup");

    version = alGetString(AL_VERSION);
    vendor = alGetString(AL_VENDOR);
    renderer = alGetString(AL_RENDERER);
    check(version != NULL && strstr(version, "1.24.1") != NULL,
          "A.null AL_VERSION reports the packaged 1.24.1 release");
    check(vendor != NULL && strcmp(vendor, "OpenAL Community") == 0,
          "A.null AL_VENDOR is \"OpenAL Community\"");
    check(renderer != NULL && strcmp(renderer, "OpenAL Soft") == 0,
          "A.null AL_RENDERER is \"OpenAL Soft\"");

    alGenBuffers(1, &buffer);
    check(buffer != 0 && alGetError() == AL_NO_ERROR,
          "A.null alGenBuffers() yields a buffer name");
    alBufferData(buffer, AL_FORMAT_MONO16, samples, (ALsizei)sizeof(samples), SAMPLE_RATE);
    check(alGetError() == AL_NO_ERROR, "A.null alBufferData(MONO16) accepted");

    alGenSources(1, &source);
    check(source != 0 && alGetError() == AL_NO_ERROR,
          "A.null alGenSources() yields a source name");
    alSourcei(source, AL_BUFFER, (ALint)buffer);
    check(alGetError() == AL_NO_ERROR, "A.null alSourcei(AL_BUFFER) accepted");
    alSourcei(source, AL_LOOPING, AL_TRUE);
    alSourcePlay(source);
    alGetSourcei(source, AL_SOURCE_STATE, &state);
    check(state == AL_PLAYING, "A.null source reaches AL_PLAYING");
    alSourceStop(source);
    alGetSourcei(source, AL_SOURCE_STATE, &state);
    check(state == AL_STOPPED, "A.null source reaches AL_STOPPED");

    /* Negative path: an invalid property must surface through alGetError(). */
    alSourcef(source, (ALenum)0xFFFF, 1.0f);
    check(alGetError() == AL_INVALID_ENUM,
          "A.null invalid property reports AL_INVALID_ENUM");

    alDeleteSources(1, &source);
    alDeleteBuffers(1, &buffer);
    check(alGetError() == AL_NO_ERROR, "A.null alDeleteSources/alDeleteBuffers clean");

    alcMakeContextCurrent(NULL);
    alcDestroyContext(context);
    check(alcCloseDevice(device) == ALC_TRUE, "A.null alcCloseDevice() succeeds");
    return 0;
}

/* ── B) loopback backend (real rendering) ───────────────────────────────── */
static int run_loopback_backend(void)
{
    static short tone[FULL_TONE_SAMPLES];
    static short rendered[TONE_SAMPLES];
    const ALCint attrs[] = {
        ALC_FORMAT_CHANNELS_SOFT, ALC_MONO_SOFT,
        ALC_FORMAT_TYPE_SOFT, ALC_SHORT_SOFT,
        ALC_FREQUENCY, SAMPLE_RATE,
        0
    };
    ALCdevice *device;
    ALCcontext *context;
    ALuint buffer = 0, source = 0;
    ALint freq = 0, state = 0;
    int peak, crossings, nonzero = 0, i;

    fill_tone(tone, FULL_TONE_SAMPLES);
    memset(rendered, 0, sizeof(rendered));

    device = alcLoopbackOpenDeviceSOFT(NULL);
    check(device != NULL, "B.loopback alcLoopbackOpenDeviceSOFT() returns a device");
    if (!device) {
        return 1;
    }
    check(alcIsExtensionPresent(device, "ALC_SOFT_loopback") == ALC_TRUE,
          "B.loopback ALC_SOFT_loopback is advertised");
    check(alcIsExtensionPresent(device, "ALC_SOFT_HRTF") == ALC_TRUE,
          "B.loopback ALC_SOFT_HRTF is advertised");

    context = alcCreateContext(device, attrs);
    check(context != NULL, "B.loopback alcCreateContext() with 8 kHz mono attrs");
    if (!context) {
        alcCloseDevice(device);
        return 1;
    }
    check(alcMakeContextCurrent(context) == ALC_TRUE,
          "B.loopback alcMakeContextCurrent() succeeds");

    alcGetIntegerv(device, ALC_FREQUENCY, 1, &freq);
    check(freq == SAMPLE_RATE, "B.loopback device runs at the requested 8 kHz");
    check(alcIsRenderFormatSupportedSOFT(device, SAMPLE_RATE, ALC_MONO_SOFT, ALC_SHORT_SOFT) == ALC_TRUE,
          "B.loopback 8 kHz/mono/short is a supported render format");

    alGenBuffers(1, &buffer);
    alBufferData(buffer, AL_FORMAT_MONO16, tone, (ALsizei)sizeof(tone), SAMPLE_RATE);
    check(alGetError() == AL_NO_ERROR, "B.loopback 8 kHz mono PCM uploaded");
    alGenSources(1, &source);
    alSourcei(source, AL_BUFFER, (ALint)buffer);
    alSourcePlay(source);
    alGetSourcei(source, AL_SOURCE_STATE, &state);
    check(state == AL_PLAYING, "B.loopback source is playing before render");

    alcRenderSamplesSOFT(device, rendered, TONE_SAMPLES);
    check(alGetError() == AL_NO_ERROR, "B.loopback alcRenderSamplesSOFT() reports no error");

    peak = peak_amplitude(rendered, TONE_SAMPLES);
    crossings = count_zero_crossings(rendered, TONE_SAMPLES);
    for (i = 0; i < TONE_SAMPLES; i++) {
        if (rendered[i] != 0) {
            nonzero++;
        }
    }

    printf("INFO: loopback peak=%d nonzero=%d/%d zero-crossings=%d\n",
           peak, nonzero, TONE_SAMPLES, crossings);

    /* The mixer must reproduce the source tone: ~0.5 full scale amplitude and
     * 2 * TONE_HZ * (TONE_SAMPLES / SAMPLE_RATE) = 52.8 zero crossings (a sine
     * crosses zero twice per period: once rising, once falling). */
    check(peak > 8000, "B.loopback rendered peak matches the 0.5 FS source tone");
    check(nonzero > TONE_SAMPLES / 2, "B.loopback render is not silence");
    check(crossings >= 46 && crossings <= 60,
          "B.loopback render reproduces the 220 Hz source frequency");

    /* Rendering a second block must keep advancing the device clock. */
    alcRenderSamplesSOFT(device, rendered, TONE_SAMPLES);
    check(peak_amplitude(rendered, TONE_SAMPLES) > 8000,
          "B.loopback second render block still carries the tone");

    alSourceStop(source);
    alDeleteSources(1, &source);
    alDeleteBuffers(1, &buffer);
    alcMakeContextCurrent(NULL);
    alcDestroyContext(context);
    check(alcCloseDevice(device) == ALC_TRUE, "B.loopback alcCloseDevice() succeeds");
    return 0;
}

int main(void)
{
    int rc = 0;

    printf("== OpenAL Soft 1.24.1 consumer test (null + loopback) ==\n");
    if (run_null_backend() != 0) {
        rc = 1;
    }
    if (run_loopback_backend() != 0) {
        rc = 2;
    }

    printf("TOTAL: %d / PASS: %d / FAIL: %d\n", g_checks, g_checks - g_failures, g_failures);
    if (g_failures != 0) {
        rc = 3;
    }
    return rc;
}
