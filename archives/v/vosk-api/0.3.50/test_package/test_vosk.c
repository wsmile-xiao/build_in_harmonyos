/*
 * Consumer test for the packaged libvosk.so — exercises the public C API
 * declared in <vosk_api.h>.
 *
 * Model-based recognition needs an external model directory (downloaded from
 * alphacephei.com) together with a wav file, so it cannot run inside
 * test_package. The assertions below therefore cover:
 *   * the C API is linkable and callable from plain C;
 *   * the documented graceful-failure contract for a missing model
 *     (vosk_model_new / vosk_spk_model_new / vosk_batch_model_new -> NULL);
 *   * a real functional path through the library: the inverse-text-normalisation
 *     processor loads two OpenFst transducers (Fst::Read) and round-trips text
 *     through StringCompiler + Compose + ShortestPath.
 *
 * usage: test_vosk <tagger.fst> <verbalizer.fst> <missing-model-dir>
 */
#include <vosk_api.h>

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int checks = 0;
static int failures = 0;

#define CHECK(cond, msg)                                                     \
    do {                                                                     \
        checks++;                                                            \
        if (cond) {                                                          \
            printf("PASS %d: %s\n", checks, msg);                            \
        } else {                                                             \
            printf("FAIL %d: %s\n", checks, msg);                            \
            failures++;                                                      \
        }                                                                    \
    } while (0)

int main(int argc, char **argv)
{
    if (argc < 4) {
        fprintf(stderr, "usage: %s <tagger.fst> <verbalizer.fst> <missing-model-dir>\n",
                argv[0]);
        return 2;
    }
    const char *tagger = argv[1];
    const char *verbalizer = argv[2];
    const char *missing_dir = argv[3];

    /* 1. log-level control is reachable (kaldi SetVerboseLevel) */
    vosk_set_log_level(-1);
    CHECK(1, "vosk_set_log_level(-1) callable");

    /* 2. a missing model directory must fail gracefully, not abort */
    VoskModel *model = vosk_model_new(missing_dir);
    CHECK(model == NULL, "vosk_model_new(missing dir) returns NULL");

    /* 3. same contract for the speaker model */
    VoskSpkModel *spk = vosk_spk_model_new(missing_dir);
    CHECK(spk == NULL, "vosk_spk_model_new(missing dir) returns NULL");

    /* 4. batch model is compiled without CUDA support -> NULL */
    VoskBatchModel *batch = vosk_batch_model_new(missing_dir);
    CHECK(batch == NULL, "vosk_batch_model_new returns NULL (built without CUDA)");

    /* 5. freeing NULL handles is a documented no-op */
    vosk_model_free(NULL);
    vosk_spk_model_free(NULL);
    CHECK(1, "vosk_model_free(NULL) / vosk_spk_model_free(NULL) are no-ops");

    /* 6. the ITN processor loads the two FSTs through OpenFst's Fst::Read */
    VoskTextProcessor *proc = vosk_text_processor_new(tagger, verbalizer);
    CHECK(proc != NULL, "vosk_text_processor_new(identity fsts) is not NULL");

    if (proc != NULL) {
        char *out;

        /* 7. byte-level identity transducer round-trip */
        out = vosk_text_processor_itn(proc, "hello 123");
        CHECK(out != NULL && strcmp(out, "hello 123") == 0,
              "vosk_text_processor_itn('hello 123') == 'hello 123'");
        free(out);

        /* 8. empty input short-circuits to an empty result */
        out = vosk_text_processor_itn(proc, "");
        CHECK(out != NULL && out[0] == '\0',
              "vosk_text_processor_itn('') == ''");
        free(out);

        /* 9. longer multi-word sentence */
        out = vosk_text_processor_itn(proc, "oh one two");
        CHECK(out != NULL && strcmp(out, "oh one two") == 0,
              "vosk_text_processor_itn('oh one two') == 'oh one two'");
        free(out);

        /* 10. release */
        vosk_text_processor_free(proc);
        CHECK(1, "vosk_text_processor_free callable");
    }

    printf("checks=%d failures=%d\n", checks, failures);
    return failures == 0 ? 0 : 1;
}
