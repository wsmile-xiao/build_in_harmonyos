/*
 * Consumer test for the sonivox Conan package.
 *
 * Drives the public EAS API against the installed library:
 *   1. library configuration contract (version, sample rate, channels),
 *   2. offline rendering of a generated Standard MIDI File through the
 *      embedded wavetable samples (must produce non-silent PCM output),
 *   3. a negative control: malformed input must be rejected.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <sonivox/eas.h>

#define MIDI_FILE "sonivox_test.mid"
#define BAD_FILE  "sonivox_test.bad"

static int g_failures = 0;

#define CHECK(cond, msg)                                     \
    do {                                                     \
        if (cond) {                                          \
            printf("PASS: %s\n", msg);                       \
        } else {                                             \
            printf("FAIL: %s\n", msg);                       \
            g_failures++;                                    \
        }                                                    \
    } while (0)

/*
 * Minimal format-0 SMF: tempo 500000 us/quarter, program change on channel 0,
 * one C4 note held for 96 ticks (96 ticks/quarter), end of track at tick 96.
 * Expected play time: 500 ms.
 */
static int write_midi_file(const char *path)
{
    static const unsigned char smf[] = {
        'M',  'T',  'h',  'd', 0x00, 0x00, 0x00, 0x06,
        0x00, 0x00,                                            /* format 0 */
        0x00, 0x01,                                            /* one track */
        0x00, 0x60,                                            /* 96 ticks per quarter note */
        'M',  'T',  'r',  'k', 0x00, 0x00, 0x00, 0x16,
        0x00, 0xFF, 0x51, 0x03, 0x07, 0xA1, 0x20,              /* tempo: 500000 us/quarter */
        0x00, 0xC0, 0x00,                                      /* program change ch0 */
        0x00, 0x90, 0x3C, 0x64,                                /* note on  C4 vel 100 */
        0x60, 0x80, 0x3C, 0x00,                                /* note off C4 */
        0x00, 0xFF, 0x2F, 0x00                                 /* end of track */
    };
    FILE *f = fopen(path, "wb");
    size_t written;

    if (f == NULL) {
        return -1;
    }
    written = fwrite(smf, 1, sizeof(smf), f);
    fclose(f);
    return written == sizeof(smf) ? 0 : -1;
}

static int write_bad_file(const char *path)
{
    static const unsigned char junk[] = {0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07};
    FILE *f = fopen(path, "wb");
    size_t written;

    if (f == NULL) {
        return -1;
    }
    written = fwrite(junk, 1, sizeof(junk), f);
    fclose(f);
    return written == sizeof(junk) ? 0 : -1;
}

int main(void)
{
    const S_EAS_LIB_CONFIG *config = EAS_Config();
    EAS_DATA_HANDLE eas = NULL;
    EAS_HANDLE stream = NULL;
    EAS_PCM *buffer = NULL;
    FILE *midi = NULL;
    EAS_FILE file;
    EAS_I32 play_time_ms = 0;
    long rendered_frames = 0;
    int peak = 0;
    int render_ok = 1;
    int guard = 0;
    int i;

    /* 1. Library configuration contract */
    CHECK(config != NULL, "EAS_Config returns a library configuration");
    if (config == NULL) {
        return 1;
    }
    CHECK(config->libVersion == MAKE_LIB_VERSION(3, 6, 16, 0), "library version is 3.6.16.0");
    CHECK(config->sampleRate == 44100, "sample rate is 44100 Hz (USE_44KHZ=ON)");
    CHECK(config->numChannels == 2, "output is stereo");
    CHECK(config->mixBufferSize > 0, "mix buffer size is positive");

    if (write_midi_file(MIDI_FILE) != 0) {
        printf("FAIL: cannot write %s\n", MIDI_FILE);
        return 1;
    }

    /* 2. Render the generated MIDI file with the embedded wavetable samples */
    CHECK(EAS_Init(&eas) == EAS_SUCCESS && eas != NULL, "EAS_Init succeeds");
    if (eas == NULL) {
        remove(MIDI_FILE);
        return 1;
    }
    CHECK(EAS_SetVolume(eas, NULL, 90) == EAS_SUCCESS, "EAS_SetVolume succeeds");

    midi = fopen(MIDI_FILE, "rb");
    CHECK(midi != NULL, "generated MIDI file opens");
    memset(&file, 0, sizeof(file));
    file.handle = midi;

    CHECK(midi != NULL && EAS_OpenFile(eas, &file, &stream) == EAS_SUCCESS && stream != NULL,
          "EAS_OpenFile accepts the generated SMF");
    CHECK(stream != NULL && EAS_Prepare(eas, stream) == EAS_SUCCESS, "EAS_Prepare succeeds");

    if (stream != NULL) {
        CHECK(EAS_ParseMetaData(eas, stream, &play_time_ms) == EAS_SUCCESS && play_time_ms > 0,
              "EAS_ParseMetaData reports a positive play time");
        CHECK(play_time_ms >= 450 && play_time_ms <= 600,
              "play time is about 500 ms for the generated SMF");
    }

    buffer = (EAS_PCM *)malloc(sizeof(EAS_PCM) * (size_t)config->mixBufferSize * (size_t)config->numChannels);
    CHECK(buffer != NULL, "PCM buffer allocation succeeds");

    while (buffer != NULL && stream != NULL && guard++ < 10000) {
        EAS_STATE state = EAS_STATE_ERROR;
        EAS_I32 count = 0;

        if (EAS_State(eas, stream, &state) != EAS_SUCCESS) {
            render_ok = 0;
            break;
        }
        if (state == EAS_STATE_STOPPED) {
            break;
        }
        if (EAS_Render(eas, buffer, config->mixBufferSize, &count) != EAS_SUCCESS) {
            render_ok = 0;
            break;
        }
        if (count != config->mixBufferSize) {
            render_ok = 0;
            break;
        }
        for (i = 0; i < count * config->numChannels; i++) {
            int sample = buffer[i];
            if (sample < 0) {
                sample = -sample;
            }
            if (sample > peak) {
                peak = sample;
            }
        }
        rendered_frames += count;
    }

    CHECK(render_ok, "render loop finishes without API errors");
    CHECK(rendered_frames >= 44100L / 2, "rendered at least 500 ms of audio");
    CHECK(peak > 0, "rendered PCM output is not silent");

    if (stream != NULL) {
        CHECK(EAS_CloseFile(eas, stream) == EAS_SUCCESS, "EAS_CloseFile succeeds");
    }
    if (midi != NULL) {
        fclose(midi);
    }
    free(buffer);
    CHECK(EAS_Shutdown(eas) == EAS_SUCCESS, "EAS_Shutdown succeeds");
    remove(MIDI_FILE);

    /* 3. Negative control: malformed input must be rejected */
    if (write_bad_file(BAD_FILE) == 0) {
        EAS_DATA_HANDLE eas2 = NULL;
        EAS_HANDLE stream2 = NULL;
        FILE *bad = NULL;
        EAS_FILE bad_file;
        EAS_RESULT open_result = EAS_FAILURE;

        if (EAS_Init(&eas2) == EAS_SUCCESS && eas2 != NULL) {
            bad = fopen(BAD_FILE, "rb");
            if (bad != NULL) {
                memset(&bad_file, 0, sizeof(bad_file));
                bad_file.handle = bad;
                open_result = EAS_OpenFile(eas2, &bad_file, &stream2);
                fclose(bad);
            }
            if (stream2 != NULL) {
                EAS_CloseFile(eas2, stream2);
            }
            EAS_Shutdown(eas2);
        }
        remove(BAD_FILE);
        CHECK(open_result != EAS_SUCCESS, "malformed input is rejected by EAS_OpenFile");
    }

    if (g_failures != 0) {
        printf("test_sonivox: %d check(s) FAILED\n", g_failures);
        return 1;
    }
    printf("test_sonivox: all checks passed\n");
    return 0;
}
