#include <mecab.h>
#include <cstdio>
#include <cstring>
#include <string>

// HarmonyOS target-environment consumption test for mecab-jumandic.
//
// Loads the binary dictionary compiled by this package's recipe
// (char.bin/matrix.bin/sys.dic/unk.dic + dicrc) through libmecab and runs
// Japanese morphological analysis on fixed samples, comparing against
// golden output captured from the same dictionary + mecab 0.996 stack.
//
// OHOS specifics verified here:
// - mecab's default rcfile is the hardcoded "//etc/mecabrc" which does NOT
//   exist on OHOS's read-only rootfs; the tagger is created with
//   "-d <dicdir> --rcfile <dicdir>/dicrc" (dicrc shipped in this package).
// - The binary indices produced by the OHOS-aarch64 mecab-dict-index are
//   consumed natively by the OHOS-aarch64 libmecab.

struct Sample {
    const char* input;
    const char* expect_first_line;  // first morpheme line of the golden output
};

static const Sample kSamples[] = {
    {"今日はいい天気なので、散歩しました。",
     "今日\t名詞,時相名詞,*,*,今日,きょう,代表表記:今日/きょう カテゴリ:時間"},
    {"すもももももももものうち",
     "すもも\t名詞,普通名詞,*,*,すもも,すもも,自動獲得:テキスト"},
    {"図書館で勉強する。",
     "図書\t名詞,普通名詞,*,*,図書,としょ,代表表記:図書/としょ カテゴリ:抽象物 ドメイン:文化・芸術"},
};

int main(int argc, char** argv) {
    if (argc < 2) {
        std::fprintf(stderr, "usage: test_package <dic_dir>\n");
        return 3;
    }
    std::string dic_dir = argv[1];
    std::string args = "-d " + dic_dir + " --rcfile " + dic_dir + "/dicrc";

    mecab_model_t* model = mecab_model_new2(args.c_str());
    if (!model) {
        std::fprintf(stderr, "FAIL: mecab_model_new2(%s): %s\n", args.c_str(), mecab_strerror(0));
        return 1;
    }
    mecab_t* tagger = mecab_model_new_tagger(model);
    if (!tagger) {
        std::fprintf(stderr, "FAIL: mecab_model_new_tagger: %s\n", mecab_strerror(0));
        return 1;
    }

    int failures = 0;
    const size_t n = sizeof(kSamples) / sizeof(kSamples[0]);
    for (size_t i = 0; i < n; ++i) {
        const char* out = mecab_sparse_tostr(tagger, kSamples[i].input);
        if (!out) {
            std::fprintf(stderr, "FAIL [%zu]: sparse_tostr(%s): %s\n", i, kSamples[i].input,
                         mecab_strerror(tagger));
            ++failures;
            continue;
        }
        // Compare the first morpheme line against the golden output.
        const char* nl = std::strchr(out, '\t') != nullptr ? std::strchr(out, '\n') : nullptr;
        std::string first_line = std::string(out, nl ? (size_t)(nl - out) : std::strlen(out));
        if (first_line != kSamples[i].expect_first_line) {
            std::fprintf(stderr, "FAIL [%zu]: golden mismatch\n  input:  %s\n  expect: %s\n  actual: %s\n",
                         i, kSamples[i].input, kSamples[i].expect_first_line, first_line.c_str());
            ++failures;
            continue;
        }
        std::string full(out);
        if (full.find("EOS") == std::string::npos) {
            std::fprintf(stderr, "FAIL [%zu]: output missing EOS\n", i);
            ++failures;
            continue;
        }
        std::printf("[PASS] sample %zu: %s\n", i, kSamples[i].input);
    }

    mecab_destroy(tagger);
    mecab_model_destroy(model);

    if (failures > 0) {
        std::fprintf(stderr, "=== mecab-jumandic OHOS consumption test FAILED: %d/%zu ===\n",
                     failures, n);
        return 1;
    }
    std::printf("=== mecab-jumandic OHOS consumption test PASSED: %zu/%zu samples ===\n", n, n);
    return 0;
}
