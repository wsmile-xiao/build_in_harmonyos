#include <alsa/asoundlib.h>

#include <stdint.h>
#include <stdio.h>

enum { FRAME_COUNT = 32, CHANNELS = 2 };

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
    int16_t samples[FRAME_COUNT * CHANNELS] = {0};
    snd_pcm_sframes_t written;
    int result = 1;

    if (require_result(
            "snd_pcm_open",
            snd_pcm_open(&pcm, "null", SND_PCM_STREAM_PLAYBACK, 0)
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
        fputs("null playback did not enter PREPARED\n", stderr);
        goto done;
    }
    if (require_result("snd_pcm_start", snd_pcm_start(pcm)) < 0)
        goto done;
    if (snd_pcm_state(pcm) != SND_PCM_STATE_RUNNING) {
        fputs("null playback did not enter RUNNING\n", stderr);
        goto done;
    }

    written = snd_pcm_writei(pcm, samples, FRAME_COUNT);
    if (written != FRAME_COUNT) {
        fprintf(stderr, "null playback wrote %ld of %d frames\n",
                (long)written, FRAME_COUNT);
        goto done;
    }
    if (require_result("snd_pcm_drain", snd_pcm_drain(pcm)) < 0)
        goto done;
    if (snd_pcm_state(pcm) != SND_PCM_STATE_SETUP) {
        fputs("null playback did not return to SETUP\n", stderr);
        goto done;
    }
    result = 0;

done:
    if (pcm != NULL && require_result("snd_pcm_close", snd_pcm_close(pcm)) < 0)
        result = 1;
    if (result == 0)
        puts("null playback lifecycle completed");
    return result;
}
