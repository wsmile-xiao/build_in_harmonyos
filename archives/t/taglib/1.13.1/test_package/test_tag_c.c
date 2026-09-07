#include <taglib/tag_c.h>

#include <stdio.h>
#include <string.h>

/* Minimal canonical 44-byte WAV header + 4 silent samples (PCM 8 kHz mono). */
static const unsigned char wav_bytes[] = {
    'R', 'I', 'F', 'F', 0x28, 0x00, 0x00, 0x00,
    'W', 'A', 'V', 'E',
    'f', 'm', 't', ' ', 0x10, 0x00, 0x00, 0x00,
    0x01, 0x00,
    0x01, 0x00,
    0x40, 0x1f, 0x00, 0x00,
    0x80, 0x3e, 0x00, 0x00,
    0x01, 0x00,
    0x08, 0x00,
    'd', 'a', 't', 'a', 0x04, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00
};

#define FAIL(msg) do { fprintf(stderr, "FAIL: %s\n", msg); return 1; } while (0)

int main(void)
{
    FILE *fp = fopen("test.wav", "wb");
    if (!fp)
        FAIL("cannot create test.wav");
    if (fwrite(wav_bytes, 1, sizeof(wav_bytes), fp) != sizeof(wav_bytes)) {
        fclose(fp);
        FAIL("short write of test.wav");
    }
    fclose(fp);

    taglib_set_string_management_enabled(1);

    /* Round 1: open, tag, save. */
    TagLib_File *file = taglib_file_new("test.wav");
    if (!file)
        FAIL("taglib_file_new returned NULL for a valid WAV file");
    if (!taglib_file_is_valid(file))
        FAIL("taglib_file_is_valid reported false for a valid WAV file");

    TagLib_Tag *tag = taglib_file_tag(file);
    if (!tag)
        FAIL("taglib_file_tag returned NULL");
    if (strlen(taglib_tag_title(tag)) != 0)
        FAIL("fresh WAV file unexpectedly had a title");

    taglib_tag_set_title(tag, "HarmonyOS");
    taglib_tag_set_artist(tag, "OpenHarmonyPC");
    taglib_tag_set_genre(tag, "Adaptation");
    taglib_tag_set_year(tag, 2026);
    taglib_tag_set_track(tag, 1);

    const TagLib_AudioProperties *props = taglib_file_audioproperties(file);
    if (!props)
        FAIL("taglib_file_audioproperties returned NULL");
    int sample_rate = taglib_audioproperties_samplerate(props);
    int channels = taglib_audioproperties_channels(props);
    if (sample_rate != 8000)
        FAIL("unexpected sample rate (expected 8000)");
    if (channels != 1)
        FAIL("unexpected channel count (expected 1)");

    if (!taglib_file_save(file))
        FAIL("taglib_file_save failed");
    taglib_file_free(file);

    /* Round 2: reopen and verify persisted metadata through the C bindings. */
    TagLib_File *file2 = taglib_file_new("test.wav");
    if (!file2 || !taglib_file_is_valid(file2))
        FAIL("reopening saved WAV file failed");
    TagLib_Tag *tag2 = taglib_file_tag(file2);
    if (!tag2)
        FAIL("taglib_file_tag returned NULL after reopen");

    char *title = taglib_tag_title(tag2);
    char *artist = taglib_tag_artist(tag2);
    if (!title || strcmp(title, "HarmonyOS") != 0)
        FAIL("title did not round-trip through the C bindings");
    if (!artist || strcmp(artist, "OpenHarmonyPC") != 0)
        FAIL("artist did not round-trip through the C bindings");
    if (taglib_tag_year(tag2) != 2026)
        FAIL("year did not round-trip through the C bindings");
    if (taglib_tag_track(tag2) != 1)
        FAIL("track did not round-trip through the C bindings");

    taglib_file_free(file2);

    printf("taglib C bindings OK: title='%s' artist='%s' rate=%d ch=%d\n",
           title, artist, sample_rate, channels);
    return 0;
}
