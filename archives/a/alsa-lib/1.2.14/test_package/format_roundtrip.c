#include <alsa/asoundlib.h>

#include <stdio.h>

int main(void)
{
    unsigned int measured = 0;
    unsigned int named = 0;
    int value;

    for (value = 0; value <= SND_PCM_FORMAT_LAST; ++value) {
        snd_pcm_format_t format = (snd_pcm_format_t)value;
        const char *name = snd_pcm_format_name(format);
        int physical_width;
        int width;

        if (name == NULL)
            continue;
        ++named;
        if (snd_pcm_format_value(name) != format) {
            fprintf(stderr, "format round-trip failed for %s\n", name);
            return 1;
        }

        width = snd_pcm_format_width(format);
        physical_width = snd_pcm_format_physical_width(format);
        if ((width < 0) != (physical_width < 0)) {
            fprintf(stderr, "inconsistent widths for %s: %d/%d\n",
                    name, width, physical_width);
            return 1;
        }
        if (width >= 0) {
            if (width == 0 || physical_width == 0 || width > physical_width) {
                fprintf(stderr, "invalid widths for %s: %d/%d\n",
                        name, width, physical_width);
                return 1;
            }
            ++measured;
        }
    }

    if (named < 40 || measured < 30) {
        fprintf(stderr, "format table was unexpectedly small: %u/%u\n",
                named, measured);
        return 1;
    }
    if (snd_pcm_format_value("conan-invalid-format") !=
        SND_PCM_FORMAT_UNKNOWN) {
        fputs("unknown format name was accepted\n", stderr);
        return 1;
    }

    printf("format table round-trip: %u named, %u with widths\n",
           named, measured);
    return 0;
}
