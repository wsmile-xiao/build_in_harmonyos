#include <mpd/audio_format.h>
#include <mpd/client.h>
#include <mpd/tag.h>
#include <mpd/version.h>

#include <stdio.h>
#include <string.h>

int main(void)
{
    if (!LIBMPDCLIENT_CHECK_VERSION(2, 23, 0))
        return 1;

    if (strcmp(mpd_tag_name(MPD_TAG_ARTIST), "Artist") != 0)
        return 2;

    if (mpd_tag_name_parse("Album") != MPD_TAG_ALBUM)
        return 3;

    if (mpd_tag_name_iparse("showmovement") != MPD_TAG_SHOWMOVEMENT)
        return 4;

    struct mpd_audio_format format = {
        .sample_rate = 44100,
        .bits = 16,
        .channels = 2
    };
    if (format.sample_rate != 44100 || format.bits != 16 || format.channels != 2)
        return 5;

    printf("libmpdclient API smoke passed\n");
    return 0;
}
