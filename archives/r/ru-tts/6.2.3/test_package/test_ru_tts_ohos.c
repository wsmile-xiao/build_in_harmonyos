#include <stdint.h>
#include <stdio.h>

#include <ru_tts.h>

#ifndef __OHOS__
#error "HarmonyOS-specific test must be compiled by the OHOS toolchain"
#endif

#ifndef __aarch64__
#error "HarmonyOS PC package must exercise the AArch64 code path"
#endif

typedef struct {
    size_t calls;
    size_t bytes;
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

static int count_audio(void *buffer, size_t size, void *user_data)
{
    audio_stats_t *stats = user_data;
    (void)buffer;
    ++stats->calls;
    stats->bytes += size;
    return 0;
}

int main(void)
{
    static const char text[] = "\xf0\xd2\xc9\xd7\xc5\xd4"; /* привет */
    unsigned char wave[127];
    ru_tts_conf_t config;
    audio_stats_t stats = {0};

    ru_tts_config_init(&config);
    CHECK(1, "compiled with the __OHOS__ platform macro");
    CHECK(1, "compiled for the AArch64 target");
    CHECK(sizeof(void *) == 8, "OHOS AArch64 uses 64-bit pointers");
    CHECK(config.speech_rate == 100 && config.voice_pitch == 100,
          "public configuration ABI is usable on OHOS");

    ru_tts_transfer(&config, text, wave, sizeof(wave), count_audio, &stats);
    CHECK(stats.calls > 1, "OHOS callback handles multiple unaligned chunks");
    CHECK(stats.bytes > 1024, "OHOS synthesis produces audio data");

    printf("test_ru_tts_ohos: %d checks, %d failures\n", checks, failures);
    return failures == 0 ? 0 : 1;
}
