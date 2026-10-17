// test_openal.cpp — openal-soft 1.25.2 test_package consumer tests.
// Verifies a consumer can link against OpenAL and use the built-in
// Null/loopback backends without any real audio device.
//
// Test cases (independently reported, counted, and failed):
//   1. NullDeviceNoOutput     — alcOpenDevice("No Output") + alcCreateContext
//   2. LoopbackContextAttributes — ALC_SOFT_loopback + alcLoopbackOpenDeviceSOFT
//                                + alcCreateContext with ALC_FORMAT_CHANNELS_SOFT /
//                                ALC_FORMAT_TYPE_SOFT / ALC_FREQUENCY
//   3. LoopbackRenderSamples  — alcRenderSamplesSOFT (960 samples) + error check
//
// NB: 1.25.2 has no alcSetFormat; the loopback format is set through the
// context attribute list (UpdateDeviceParams in alc.cpp).
#include <AL/al.h>
#include <AL/alc.h>
#define AL_ALEXT_PROTOTYPES
#include <AL/alext.h>

#include <cstdio>
#include <cstring>
#include <cstdint>

static int g_case_total = 0;
static int g_case_pass = 0;
static int g_case_fail = 0;

static void report(const char* caseName, bool ok, const char* why)
{
    ++g_case_total;
    if(ok) ++g_case_pass; else ++g_case_fail;
    std::printf("[%s] %s: %s\n", ok ? "PASS" : "FAIL", caseName, why);
}

/* Case 1: NullDeviceNoOutput — null backend device + context */
static void runNullDeviceNoOutput()
{
    ALCdevice* nulldev = alcOpenDevice("No Output");
    if(!nulldev)
    {
        report("NullDeviceNoOutput", false, "alcOpenDevice(No Output) returned NULL");
        return;
    }
    ALCcontext* ctx = alcCreateContext(nulldev, nullptr);
    if(!ctx)
    {
        alcCloseDevice(nulldev);
        report("NullDeviceNoOutput", false, "alcCreateContext failed on null device");
        return;
    }
    alcMakeContextCurrent(ctx);
    const bool current_ok = alcGetCurrentContext() == ctx;
    alcMakeContextCurrent(nullptr);
    alcDestroyContext(ctx);
    alcCloseDevice(nulldev);

    report("NullDeviceNoOutput", current_ok,
        current_ok ? "null device + context created and made current" : "context not current");
}

/* Case 2: LoopbackContextAttributes — extension + loopback device + attrs */
static void runLoopbackContextAttributes()
{
    ALCdevice* extdev = alcOpenDevice(nullptr);
    const bool ext_present = extdev
        && alcIsExtensionPresent(extdev, "ALC_SOFT_loopback") == ALC_TRUE;
    if(extdev) alcCloseDevice(extdev);
    if(!ext_present)
    {
        report("LoopbackContextAttributes", false, "ALC_SOFT_loopback NOT advertised");
        return;
    }

    ALCdevice* loopdev = alcLoopbackOpenDeviceSOFT(nullptr);
    if(!loopdev)
    {
        report("LoopbackContextAttributes", false, "alcLoopbackOpenDeviceSOFT returned NULL");
        return;
    }

    const ALCint attrs[] = {
        ALC_FORMAT_CHANNELS_SOFT, ALC_STEREO_SOFT,
        ALC_FORMAT_TYPE_SOFT, ALC_SHORT_SOFT,
        ALC_FREQUENCY, 48000,
        0
    };
    ALCcontext* loopctx = alcCreateContext(loopdev, attrs);
    const bool ctx_ok = loopctx != nullptr && alcGetError(loopdev) == ALC_NO_ERROR;
    if(loopctx) alcDestroyContext(loopctx);
    /* keep device open for case 3 */
    report("LoopbackContextAttributes", ctx_ok,
        ctx_ok ? "loopback device + stereo/16bit/48k context via attribute list accepted"
               : "alcCreateContext with loopback attributes failed");
}

/* Case 3: LoopbackRenderSamples — render 960 samples on a loopback device */
static void runLoopbackRenderSamples()
{
    ALCdevice* loopdev = alcLoopbackOpenDeviceSOFT(nullptr);
    if(!loopdev)
    {
        report("LoopbackRenderSamples", false, "alcLoopbackOpenDeviceSOFT returned NULL");
        return;
    }

    const ALCint attrs[] = {
        ALC_FORMAT_CHANNELS_SOFT, ALC_STEREO_SOFT,
        ALC_FORMAT_TYPE_SOFT, ALC_SHORT_SOFT,
        ALC_FREQUENCY, 48000,
        0
    };
    ALCcontext* loopctx = alcCreateContext(loopdev, attrs);
    if(!loopctx)
    {
        alcCloseDevice(loopdev);
        report("LoopbackRenderSamples", false, "alcCreateContext(loopback) failed");
        return;
    }

    std::int16_t buf[960 * 2];
    std::memset(buf, 0, sizeof(buf));
    alcRenderSamplesSOFT(loopdev, buf, 960);
    const ALCenum err = alcGetError(loopdev);

    alcDestroyContext(loopctx);
    alcCloseDevice(loopdev);

    report("LoopbackRenderSamples", err == ALC_NO_ERROR,
        err == ALC_NO_ERROR ? "960 samples rendered, no error"
        : "alcGetError after alcRenderSamplesSOFT != ALC_NO_ERROR");
}

int main()
{
    runNullDeviceNoOutput();
    runLoopbackContextAttributes();
    runLoopbackRenderSamples();

    std::printf("SUMMARY: %d case(s), %d passed, %d failed\n",
        g_case_total, g_case_pass, g_case_fail);
    return g_case_fail == 0 ? 0 : 1;
}
