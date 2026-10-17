// Consumer test for mecab-unidic-extended 2.1.2.
//
// Links libmecab (from the mecab/0.996 package), loads the packaged UniDic
// binary indices via mecab_new2("-d <dicdir> -r <rcfile>") and verifies:
//   1. UNIDIC_EXT_DICDIR (runenv exported by the package) matches the
//      dictionary directory passed as argv[1]
//   2. tokenization of すもももももももものうち matches the golden output
//      captured from a verified on-device build, line by line — including
//      the unidic 8-column output format with the aType accent column
//   3. a second sentence (形態素解析は面白い) tokenizes with the expected
//      morphemes and EOS
//
// HarmonyOS has no system mecabrc (/usr/local/etc/mecabrc does not exist),
// so the consumer passes an explicitly empty rc file via -r; the dictionary
// directory's dicrc carries the output-format configuration.
#include <mecab.h>

#include <cstdlib>
#include <iostream>
#include <string>
#include <vector>

namespace {

const char *kGolden[] = {
    "すもも\tスモモ\tスモモ\t李\t名詞-普通名詞-一般\t\t\t0",
    "も\tモ\tモ\tも\t助詞-係助詞\t\t\t",
    "もも\tモモ\tモモ\t桃\t名詞-普通名詞-一般\t\t\t0",
    "も\tモ\tモ\tも\t助詞-係助詞\t\t\t",
    "もも\tモモ\tモモ\t桃\t名詞-普通名詞-一般\t\t\t0",
    "の\tノ\tノ\tの\t助詞-格助詞\t\t\t",
    "うち\tウチ\tウチ\t内\t名詞-普通名詞-副詞可能\t\t\t0",
    "EOS",
};

std::vector<std::string> split_lines(const std::string &out) {
    std::vector<std::string> lines;
    size_t pos = 0;
    while (pos < out.size()) {
        size_t eol = out.find('\n', pos);
        if (eol == std::string::npos) {
            break;
        }
        lines.push_back(out.substr(pos, eol - pos));
        pos = eol + 1;
    }
    return lines;
}

}  // namespace

int main(int argc, char **argv) {
    if (argc < 3) {
        std::cerr << "usage: " << argv[0] << " <dicdir> <rcfile>" << std::endl;
        return 2;
    }
    const std::string dicdir = argv[1];
    const std::string rcfile = argv[2];

    // 1. UNIDIC_EXT_DICDIR env contract (exported via the package runenv)
    const char *envdic = std::getenv("UNIDIC_EXT_DICDIR");
    if (envdic == nullptr || dicdir != envdic) {
        std::cerr << "FAIL: UNIDIC_EXT_DICDIR="
                  << (envdic ? envdic : "<unset>") << " != " << dicdir << std::endl;
        return 1;
    }
    std::cout << "UNIDIC_EXT_DICDIR: " << envdic << std::endl;

    mecab_t *mecab = mecab_new2(("-d " + dicdir + " -r " + rcfile).c_str());
    if (mecab == nullptr) {
        std::cerr << "FAIL: mecab_new2: " << mecab_strerror(nullptr) << std::endl;
        return 1;
    }
    std::cout << "mecab version: " << mecab_version() << std::endl;
    std::cout << "dictionary dir: " << dicdir << std::endl;

    // 2. Golden sentence
    const char *result = mecab_sparse_tostr(mecab, "すもももももももものうち");
    if (result == nullptr) {
        std::cerr << "FAIL: mecab_sparse_tostr: " << mecab_strerror(mecab) << std::endl;
        mecab_destroy(mecab);
        return 1;
    }
    std::cout << "--- golden sentence: すもももももももものうち ---" << std::endl;
    std::cout << result;

    const std::vector<std::string> lines = split_lines(result);
    const size_t expected = sizeof(kGolden) / sizeof(kGolden[0]);
    if (lines.size() != expected) {
        std::cerr << "FAIL: " << lines.size() << " output lines, expected " << expected << std::endl;
        mecab_destroy(mecab);
        return 1;
    }
    for (size_t i = 0; i < expected; ++i) {
        if (lines[i] != kGolden[i]) {
            std::cerr << "FAIL: line " << (i + 1) << " mismatch:" << std::endl;
            std::cerr << "  expected: [" << kGolden[i] << "]" << std::endl;
            std::cerr << "  actual:   [" << lines[i] << "]" << std::endl;
            mecab_destroy(mecab);
            return 1;
        }
    }
    std::cout << "golden match: " << expected << "/" << expected << " lines OK" << std::endl;

    // 3. Second sentence
    const char *result2 = mecab_sparse_tostr(mecab, "形態素解析は面白い");
    if (result2 == nullptr) {
        std::cerr << "FAIL: mecab_sparse_tostr: " << mecab_strerror(mecab) << std::endl;
        mecab_destroy(mecab);
        return 1;
    }
    std::cout << "--- second sentence: 形態素解析は面白い ---" << std::endl;
    std::cout << result2;
    const std::string out2(result2);
    // UniDic 2.1.2 has no single 形態素 lexeme (lex.csv carries 形態 and 素
    // as separate entries), so the sentence tokenizes as 5 morphemes:
    // 形態 / 素 / 解析 / は / 面白い — verified against the on-device build.
    const bool ok2 = out2.find("形態\t") != std::string::npos &&
                     out2.find("素\t") != std::string::npos &&
                     out2.find("解析\t") != std::string::npos &&
                     out2.find("は\t") != std::string::npos &&
                     out2.find("面白い\t") != std::string::npos &&
                     out2.find("EOS") != std::string::npos;
    mecab_destroy(mecab);
    if (!ok2) {
        std::cerr << "FAIL: second sentence missing expected morphemes/EOS" << std::endl;
        return 1;
    }

    std::cout << "MECAB-UNIDIC-EXTENDED CONSUMER TEST PASSED" << std::endl;
    return 0;
}
