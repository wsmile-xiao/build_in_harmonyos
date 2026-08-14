#include <alsa/asoundlib.h>

#include <stdint.h>
#include <stdio.h>
#include <string.h>

enum { FRAME_COUNT = 37, CHANNELS = 2 };

static int require_result(const char *operation, int result)
{
    if (result >= 0)
        return 0;
    fprintf(stderr, "%s failed: %s\n", operation, snd_strerror(result));
    return -1;
}

int main(void)
{
    snd_pcm_t *pcm = NULL;
    unsigned char samples[FRAME_COUNT * CHANNELS * sizeof(int16_t)];
    unsigned char expected[sizeof(samples)];
    snd_pcm_sframes_t received;
    int result = 1;

    memset(samples, 0x5a, sizeof(samples));
    memcpy(expected, samples, sizeof(samples));

    if (require_result(
            "snd_pcm_open",
            snd_pcm_open(&pcm, "null", SND_PCM_STREAM_CAPTURE, 0)
        ) < 0)
        goto done;
    if (require_result(
            "snd_pcm_set_params",
            snd_pcm_set_params(
                pcm,
                SND_PCM_FORMAT_S16_LE,
                SND_PCM_ACCESS_RW_INTERLEAVED,
                CHANNELS,
                48000,
                0,
                100000
            )
        ) < 0)
        goto done;
    if (require_result("snd_pcm_prepare", snd_pcm_prepare(pcm)) < 0)
        goto done;
    if (snd_pcm_state(pcm) != SND_PCM_STATE_PREPARED) {
        fputs("null capture did not enter PREPARED\n", stderr);
        goto done;
    }
    if (require_result("snd_pcm_start", snd_pcm_start(pcm)) < 0)
        goto done;
    if (snd_pcm_state(pcm) != SND_PCM_STATE_RUNNING) {
        fputs("null capture did not enter RUNNING\n", stderr);
        goto done;
    }

    received = snd_pcm_readi(pcm, samples, FRAME_COUNT);
    if (received != FRAME_COUNT) {
        fprintf(stderr, "null capture read %ld of %d frames\n",
                (long)received, FRAME_COUNT);
        goto done;
    }
    if (memcmp(samples, expected, sizeof(samples)) != 0) {
        fputs("null capture unexpectedly modified the destination\n", stderr);
        goto done;
    }
    if (require_result("snd_pcm_drop", snd_pcm_drop(pcm)) < 0)
        goto done;
    if (snd_pcm_state(pcm) != SND_PCM_STATE_SETUP) {
        fputs("null capture did not return to SETUP\n", stderr);
        goto done;
    }
    result = 0;

done:
    if (pcm != NULL && require_result("snd_pcm_close", snd_pcm_close(pcm)) < 0)
        result = 1;
    if (result == 0)
        puts("null capture lifecycle completed without writing data");
    return result;
}
