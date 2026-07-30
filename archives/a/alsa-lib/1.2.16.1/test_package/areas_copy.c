#include <alsa/asoundlib.h>

#include <stdint.h>
#include <stdio.h>

enum {
    CHANNELS = 2,
    SOURCE_FRAMES = 9,
    DESTINATION_FRAMES = 11,
    SOURCE_OFFSET = 2,
    DESTINATION_OFFSET = 3,
    COPY_FRAMES = 4,
};

int main(void)
{
    const uint16_t sentinel = UINT16_C(0x7b7b);
    snd_pcm_channel_area_t destination_areas[CHANNELS];
    snd_pcm_channel_area_t source_areas[CHANNELS];
    uint16_t destination[DESTINATION_FRAMES][CHANNELS];
    uint16_t source[SOURCE_FRAMES][CHANNELS];
    unsigned int channel;
    unsigned int frame;
    int result;

    for (frame = 0; frame < SOURCE_FRAMES; ++frame)
        for (channel = 0; channel < CHANNELS; ++channel)
            source[frame][channel] =
                (uint16_t)(UINT16_C(0x1000) + frame * 16U + channel);
    for (frame = 0; frame < DESTINATION_FRAMES; ++frame)
        for (channel = 0; channel < CHANNELS; ++channel)
            destination[frame][channel] = sentinel;

    for (channel = 0; channel < CHANNELS; ++channel) {
        source_areas[channel].addr = source;
        source_areas[channel].first = channel * 16U;
        source_areas[channel].step = CHANNELS * 16U;
        destination_areas[channel].addr = destination;
        destination_areas[channel].first = channel * 16U;
        destination_areas[channel].step = CHANNELS * 16U;
    }

    result = snd_pcm_areas_copy(
        destination_areas,
        DESTINATION_OFFSET,
        source_areas,
        SOURCE_OFFSET,
        CHANNELS,
        COPY_FRAMES,
        SND_PCM_FORMAT_S16_LE
    );
    if (result < 0) {
        fprintf(stderr, "snd_pcm_areas_copy failed: %d\n", result);
        return 1;
    }

    for (frame = 0; frame < DESTINATION_FRAMES; ++frame) {
        const int selected = frame >= DESTINATION_OFFSET &&
                             frame < DESTINATION_OFFSET + COPY_FRAMES;
        for (channel = 0; channel < CHANNELS; ++channel) {
            uint16_t expected = sentinel;
            if (selected) {
                expected = source[
                    SOURCE_OFFSET + frame - DESTINATION_OFFSET
                ][channel];
            }
            if (destination[frame][channel] != expected) {
                fprintf(stderr, "unexpected copy at frame %u channel %u\n",
                        frame, channel);
                return 1;
            }
        }
    }

    puts("interleaved area copy honored both offsets and sentinels");
    return 0;
}
