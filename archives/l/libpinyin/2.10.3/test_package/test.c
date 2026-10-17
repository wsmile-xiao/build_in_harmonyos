#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <pinyin.h>

#ifndef SYSTEM_DATADIR
#define SYSTEM_DATADIR NULL
#endif

static int failures = 0;

#define CHECK(condition, label) do { \
    if (condition) printf("ok - %s\n", label); \
    else { fprintf(stderr, "FAIL - %s\n", label); failures++; } \
} while (0)

int main(void)
{
    char path[1024];
    snprintf(path, sizeof(path), "%s/punct.bin", SYSTEM_DATADIR);
    FILE *punct = fopen(path, "rb");
    CHECK(punct != NULL, "model20 punctuation model is installed");
    if (punct) fclose(punct);

    pinyin_context_t *context = pinyin_init(SYSTEM_DATADIR, NULL);
    CHECK(context != NULL, "pinyin_init loads installed model data");
    if (!context) return 1;

    pinyin_instance_t *instance = pinyin_alloc_instance(context);
    CHECK(instance != NULL, "pinyin_alloc_instance");
    if (instance) {
        const char *input = "ni'hao";
        size_t parsed = pinyin_parse_more_full_pinyins(instance, input);
        CHECK(parsed == strlen(input), "parse both pinyin syllables");
        CHECK(pinyin_guess_sentence(instance) == TRUE, "guess sentence");
        char *sentence = NULL;
        pinyin_get_sentence(instance, 0, &sentence);
        CHECK(sentence != NULL, "get guessed sentence");
        g_free(sentence);
        CHECK(pinyin_reset(instance) == TRUE, "reset instance");
        pinyin_free_instance(instance);
    }
    pinyin_fini(context);
    return failures == 0 ? 0 : 1;
}
