/* test.c — consumer test for mimic/1.3.0.1 (OHOS aarch64).
 *
 * Links the *installed* libttsmimic static archives and drives the real
 * public API (include/ttsmimic/mimic.h) end-to-end: registers the HTS
 * voice shipped in the package, synthesizes speech from text into an
 * in-memory cst_wave, saves a RIFF/WAVE file and validates the result.
 *
 * The machine running this test IS the OHOS aarch64 target, so the whole
 * pipeline (text → tokens → HTS synthesis → PCM → RIFF) executes
 * natively — a real end-to-end run of the TTS engine.
 *
 * Voice loading note: mimic_voice_load() supports CG (.flitevox) voices
 * only; the HTS voice (cmu_us_slt_hts) is registered through its voice
 * constructor (register_cmu_us_slt_hts), exactly how upstream's
 * mimic_voice_list.c does it. The HTS engine locates the .htsvoice data
 * file relative to the CWD at synthesis time (./voices, ../voices, .),
 * so the test chdirs into the packaged voices directory first.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include "mimic.h"
#include "cst_wave.h"

/* voice constructor exported by libttsmimic_lang_cmu_us_slt_hts
 * (declared here the same way main/mimic_voice_list.c declares it) */
cst_voice *register_cmu_us_slt_hts(const char *voxdir);

static int failures = 0;

#define CHECK(cond, msg)                                                   \
    do {                                                                   \
        if (cond) {                                                        \
            printf("PASS %s\n", msg);                                      \
        } else {                                                           \
            printf("FAIL %s\n", msg);                                      \
            failures++;                                                    \
        }                                                                  \
    } while (0)

int main(int argc, char **argv)
{
    /* argv[1] = voices dir inside the package (holds cmu_us_slt_hts.htsvoice) */
    if (argc < 2) {
        fprintf(stderr, "usage: %s <voices-dir>\n", argv[0]);
        return 2;
    }

    /* 1. init the TTS engine */
    int rc0 = mimic_init();
    CHECK(rc0 == 0, "mimic_init() == 0");

    /* 2. HTS engine resolves the voice file relative to the CWD */
    CHECK(chdir(argv[1]) == 0, "chdir into packaged voices dir");

    /* 3. register the packaged HTS voice (upstream sequence) */
    cst_voice *v = register_cmu_us_slt_hts(".");
    CHECK(v != NULL, "register_cmu_us_slt_hts() built the voice");
    if (!v) {
        printf("%d FAILURE(S)\n", failures);
        return 1;
    }
    CHECK(strcmp(v->name, "slt_hts") == 0, "voice name is slt_hts");

    /* 4. text → speech: synthesize into an in-memory cst_wave */
    cst_wave *w = mimic_text_to_wave("hello, harmony oh os test", v);
    CHECK(w != NULL, "mimic_text_to_wave() produced a wave");
    if (w) {
        /* 5. sanity of the synthesized audio */
        CHECK(w->num_samples > 1000, "wave has real samples (>1000)");
        CHECK(w->sample_rate > 8000 && w->sample_rate <= 48000,
              "wave sample rate sane");
        CHECK(w->num_channels == 1, "wave is mono");
        int nonzero = 0;
        for (int i = 0; i < w->num_samples && i < 100000; i++)
            if (w->samples[i] != 0) nonzero++;
        CHECK(nonzero > 100, "wave is not silence");

        /* 6. save RIFF (0 == success, -1 == failure) */
        int ns = cst_wave_save_riff(w, "mimic_test.wav");
        CHECK(ns == 0, "cst_wave_save_riff() wrote the wav (rc==0)");
        FILE *f = fopen("mimic_test.wav", "rb");
        if (f) {
            char hdr[12];
            size_t got = fread(hdr, 1, 12, f);
            fclose(f);
            CHECK(got == 12 && memcmp(hdr, "RIFF", 4) == 0 &&
                  memcmp(hdr + 8, "WAVE", 4) == 0,
                  "wav file has RIFF/WAVE magic");
        } else {
            CHECK(0, "wav file readable");
        }
        delete_wave(w);
    }

    /* 7. mimic_text_to_speech with outtype "none": returns 0 on success,
     * duration comes back through *dur */
    float dur = 0.0f;
    int n2 = mimic_text_to_speech("one two three four five", v, "none", &dur);
    CHECK(n2 == 0, "mimic_text_to_speech('none') rc==0");
    CHECK(dur > 0.1f, "mimic_text_to_speech reported duration > 0.1s");
    printf("  second synthesis: %d samples, %.2fs\n", n2, (double)dur);

    /* 8. feature access API (public wrappers) */
    cst_features *f = new_features();
    mimic_feat_set_int(f, "test.int", 42);
    CHECK(mimic_get_param_int(f, "test.int", 0) == 42,
          "mimic_feat_set_int/get_param_int round-trip");
    delete_features(f);

    /* 9. second registration returns the same voice (idempotent) */
    cst_voice *v2 = register_cmu_us_slt_hts(".");
    CHECK(v2 == v, "second register_cmu_us_slt_hts() is idempotent");
    cst_wave *w2 = mimic_text_to_wave("testing one two three", v2);
    CHECK(w2 != NULL && w2->num_samples > 500,
          "second synthesis produced samples");
    if (w2) delete_wave(w2);

    /* 10. shutdown */
    int rcx = mimic_exit();
    CHECK(rcx == 0, "mimic_exit() == 0");

    if (failures > 0) {
        printf("%d FAILURE(S)\n", failures);
        return 1;
    }
    printf("ALL PASS\n");
    return 0;
}
