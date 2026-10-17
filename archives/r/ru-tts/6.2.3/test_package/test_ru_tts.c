#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include <ru_tts.h>

typedef struct {
    size_t calls;
    size_t bytes;
    uint64_t hash;
    size_t nonzero;
} audio_stats_t;

static int failures;
static int checks;

#define CHECK(condition, label)                                                 \
    do {                                                                        \
        ++checks;                                                               \
        if (condition) {                                                        \
            printf("[ok] %s\n", label);                                       \
        } else {                                                                \
            fprintf(stderr, "[FAIL] %s\n", label);                            \
            ++failures;                                                         \
        }                                                                       \
    } while (0)

static int collect_audio(void *buffer, size_t size, void *user_data)
{
    const unsigned char *bytes = buffer;
    audio_stats_t *stats = user_data;
    size_t index;

    ++stats->calls;
    stats->bytes += size;
    for (index = 0; index < size; ++index) {
        stats->hash = (stats->hash * UINT64_C(1099511628211)) ^ bytes[index];
        stats->nonzero += bytes[index] != 0;
    }
    return 0;
}

static int stop_after_first_chunk(void *buffer, size_t size, void *user_data)
{
    audio_stats_t *stats = user_data;
    (void)buffer;
    ++stats->calls;
    stats->bytes += size;
    return 1;
}

int main(void)
{
    static const char text[] = "\xf0\xd2\xc9\xd7\xc5\xd4"; /* привет */
    unsigned char wave[256];
    ru_tts_conf_t config;
    audio_stats_t normal = {0};
    audio_stats_t alternative = {0};
    audio_stats_t stopped = {0};

    ru_tts_config_init(&config);
    CHECK(config.speech_rate == 100, "default speech rate");
    CHECK(config.voice_pitch == 100, "default voice pitch");
    CHECK(config.intonation == 100, "default intonation");
    CHECK(config.general_gap_factor == 100 && config.dot_gap_factor == 100,
          "default gap factors");
    CHECK(config.flags == (DEC_SEP_POINT | DEC_SEP_COMMA),
          "default decimal separator flags");

    ru_tts_transfer(&config, text, wave, sizeof(wave), collect_audio, &normal);
    CHECK(normal.calls > 0, "synthesis invokes consumer callback");
    CHECK(normal.bytes > 1024, "synthesis produces a complete audio stream");
    CHECK(normal.nonzero > 0, "synthesis output contains signal data");
    CHECK(normal.hash != 0, "synthesis output has a stable nonzero digest");

    config.flags |= USE_ALTERNATIVE_VOICE;
    ru_tts_transfer(
        &config, text, wave, sizeof(wave), collect_audio, &alternative);
    CHECK(alternative.bytes > 1024, "alternative voice produces audio");
    CHECK(alternative.hash != normal.hash, "voice flag changes synthesized audio");

    ru_tts_config_init(&config);
    ru_tts_transfer(
        &config, text, wave, sizeof(wave), stop_after_first_chunk, &stopped);
    CHECK(stopped.calls > 0 && stopped.calls < normal.calls,
          "nonzero callback result stops synthesis early");

    printf("test_ru_tts: %d checks, %d failures\n", checks, failures);
    return failures == 0 ? 0 : 1;
}
