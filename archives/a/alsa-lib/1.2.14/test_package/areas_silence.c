#include <alsa/asoundlib.h>

#include <stdint.h>
#include <stdio.h>

enum {
    CHANNELS = 2,
    FRAMES = 9,
    START_FRAME = 2,
    SILENT_FRAMES = 4,
};

int main(void)
{
    const uint16_t sentinel = UINT16_C(0x5a5a);
    snd_pcm_channel_area_t areas[CHANNELS];
    uint16_t samples[FRAMES][CHANNELS];
    unsigned int channel;
    unsigned int frame;
    int result;

    for (frame = 0; frame < FRAMES; ++frame)
        for (channel = 0; channel < CHANNELS; ++channel)
            samples[frame][channel] = sentinel;

    for (channel = 0; channel < CHANNELS; ++channel) {
        areas[channel].addr = samples;
        areas[channel].first = channel * 16U;
        areas[channel].step = CHANNELS * 16U;
    }

    result = snd_pcm_areas_silence(
        areas, START_FRAME, CHANNELS, SILENT_FRAMES, SND_PCM_FORMAT_S16_LE
    );
    if (result < 0) {
        fprintf(stderr, "snd_pcm_areas_silence failed: %d\n", result);
        return 1;
    }

    for (frame = 0; frame < FRAMES; ++frame) {
        const int selected =
            frame >= START_FRAME && frame < START_FRAME + SILENT_FRAMES;
        for (channel = 0; channel < CHANNELS; ++channel) {
            const uint16_t expected = selected ? 0 : sentinel;
            if (samples[frame][channel] != expected) {
                fprintf(stderr, "unexpected sample at frame %u channel %u\n",
                        frame, channel);
                return 1;
            }
        }
    }

    puts("interleaved area silence preserved both sentinels");
    return 0;
}
