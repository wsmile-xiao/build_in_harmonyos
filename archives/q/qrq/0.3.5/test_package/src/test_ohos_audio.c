/*
 * HarmonyOS-specific test for the qrq OHAudio port.
 *
 * qrq's HarmonyOS backend drives the native OHAudio renderer
 * (OH_AudioStreamBuilder / OH_AudioRenderer).  Since qrq is an interactive
 * TUI, this test exercises that renderer directly: it creates a renderer
 * with the same configuration used by ohosaudio.c, streams a short synthetic
 * 700 Hz CW tone through the write-data callback and verifies that the whole
 * waveform was consumed.
 *
 * Exit code 0 on success (prints OHOS_AUDIO_PASS), 1 otherwise.
 */

#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

#include <ohaudio/native_audiostreambuilder.h>
#include <ohaudio/native_audiorenderer.h>

#define RATE      44100
#define TONE_HZ   700
#define FRAMES    (RATE / 4)        /* 0.25 s of tone */
#define MAX_WAIT  200               /* 200 * 10 ms = 2 s */

static short tone[FRAMES];
static int   pos = 0;
static int   callbacks = 0;

static OH_AudioData_Callback_Result on_write_data(OH_AudioRenderer *renderer,
        void *user_data, void *audio_data, int32_t audio_data_size)
{
    short *out = (short *) audio_data;
    int frames = audio_data_size / (int) sizeof(short);
    int i;

    (void) renderer;
    (void) user_data;

    for (i = 0; i < frames; ++i) {
        out[i] = (pos < FRAMES) ? tone[pos] : 0;
        ++pos;
    }
    ++callbacks;
    return AUDIO_DATA_CALLBACK_RESULT_VALID;
}

int main(void)
{
    OH_AudioStreamBuilder *builder = NULL;
    OH_AudioRenderer *renderer = NULL;
    OH_AudioStream_Result res;
    int i, rc = 1;

    for (i = 0; i < FRAMES; ++i) {
        tone[i] = (short) (12000.0 * sin(2.0 * 3.14159265358979323846 * TONE_HZ * i / RATE));
    }

    if (OH_AudioStreamBuilder_Create(&builder, AUDIOSTREAM_TYPE_RENDERER) != AUDIOSTREAM_SUCCESS) {
        printf("OHOS_AUDIO_FAIL: stream builder create\n");
        return 1;
    }

    OH_AudioStreamBuilder_SetSamplingRate(builder, RATE);
    OH_AudioStreamBuilder_SetChannelCount(builder, 1);
    OH_AudioStreamBuilder_SetSampleFormat(builder, AUDIOSTREAM_SAMPLE_S16LE);
    OH_AudioStreamBuilder_SetEncodingType(builder, AUDIOSTREAM_ENCODING_TYPE_RAW);
    OH_AudioStreamBuilder_SetLatencyMode(builder, AUDIOSTREAM_LATENCY_MODE_NORMAL);
    OH_AudioStreamBuilder_SetRendererInfo(builder, AUDIOSTREAM_USAGE_MUSIC);
    OH_AudioStreamBuilder_SetRendererWriteDataCallback(builder, on_write_data, NULL);

    res = OH_AudioStreamBuilder_GenerateRenderer(builder, &renderer);
    if (res != AUDIOSTREAM_SUCCESS || renderer == NULL) {
        printf("OHOS_AUDIO_FAIL: generate renderer (%d)\n", (int) res);
        goto out;
    }

    res = OH_AudioRenderer_Start(renderer);
    if (res != AUDIOSTREAM_SUCCESS) {
        printf("OHOS_AUDIO_FAIL: renderer start (%d)\n", (int) res);
        goto out;
    }

    /* Wait until the renderer pulled the whole waveform, then let the
       hardware buffer drain. */
    for (i = 0; i < MAX_WAIT && pos < FRAMES; ++i) {
        usleep(10000);
    }
    usleep(200000);
    OH_AudioRenderer_Stop(renderer);

    if (callbacks > 0 && pos >= FRAMES) {
        printf("OHOS_AUDIO_PASS: callbacks=%d frames=%d\n", callbacks, pos);
        rc = 0;
    } else {
        printf("OHOS_AUDIO_FAIL: callbacks=%d frames=%d (expected >=%d)\n",
               callbacks, pos, FRAMES);
    }

out:
    if (renderer != NULL) {
        OH_AudioRenderer_Release(renderer);
    }
    OH_AudioStreamBuilder_Destroy(builder);
    return rc;
}
