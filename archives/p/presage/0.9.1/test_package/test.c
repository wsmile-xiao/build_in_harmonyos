/*
 * presage 0.9.1 consumer test (test_package).
 *
 * Exercises the installed library the way a real consumer would:
 *   1. presage_new_with_config() with the generated profile (argv[1])
 *   2. presage_predict()       — trained ngram DB must yield the selector
 *                                default of exactly 6 suggestions
 *   3. presage_config()        — configuration fingerprint SUGGESTIONS == 6
 *   4. presage_learn()         — online learning round-trip
 *
 * The C API callbacks take a single void* and return a const char* stream
 * (see src/lib/presageCallback.h).
 */
#include <presage.h>
#include <stdio.h>
#include <string.h>

static const char* g_past = "hello ";

static const char* past_cb(void* arg) {
    (void)arg;
    return g_past;
}

static const char* future_cb(void* arg) {
    (void)arg;
    return "";
}

#define CHECK(cond, msg)                                        \
    do {                                                        \
        if (!(cond)) {                                          \
            fprintf(stderr, "FAIL: %s\n", (msg));               \
            return 1;                                           \
        }                                                       \
        printf("[ok] %s\n", (msg));                             \
    } while (0)

int main(int argc, char** argv) {
    if (argc < 2) {
        fprintf(stderr, "usage: test_presage <presage-profile.xml>\n");
        return 2;
    }

    /* 1. context creation with consumer-provided profile */
    presage_t ctx = NULL;
    presage_error_code_t rc =
        presage_new_with_config(past_cb, NULL, future_cb, NULL, argv[1], &ctx);
    CHECK(rc == PRESAGE_OK && ctx != NULL, "presage_new_with_config");

    /* 2. prediction round-trip against the packaged trained DB */
    char** preds = NULL;
    rc = presage_predict(ctx, &preds);
    CHECK(rc == PRESAGE_OK && preds != NULL, "presage_predict");

    int n = 0;
    while (preds && preds[n] != NULL) {
        n++;
    }
    printf("predictions=%d first=%s\n", n, n > 0 ? preds[0] : "(none)");
    CHECK(n == 6, "prediction count equals Presage.Selector.SUGGESTIONS (6)");
    CHECK(preds[0][0] != '\0', "first suggestion non-empty");
    presage_free_string_array(preds);

    /* 3. configuration fingerprint (content identity of the loaded profile) */
    char* value = NULL;
    rc = presage_config(ctx, "Presage.Selector.SUGGESTIONS", &value);
    CHECK(rc == PRESAGE_OK && value != NULL && strcmp(value, "6") == 0,
          "config fingerprint Presage.Selector.SUGGESTIONS == 6");
    if (value != NULL) {
        presage_free_string(value);
    }

    /* 4. online learning round-trip */
    rc = presage_learn(ctx, "harmony presage predictive entry ");
    CHECK(rc == PRESAGE_OK, "presage_learn");

    presage_free(ctx);
    printf("test presage consumer: OK\n");
    return 0;
}
