/* Consumer test for libkytea 0.4.7 (installed headers + library).
 * Exercises the same public API paths as upstream test-kytea:
 *   1) StringUtilUtf8 mapString/getTypeString        (TestKytea)
 *   2) FullCorpusIO tagged-corpus parse              (TestCorpusIO)
 *   3) KyteaConfig + Kytea::trainAll + calculateWS   (TestAnalysis)
 */
#include <kytea/kytea.h>
#include <kytea/kytea-config.h>
#include <kytea/string-util.h>
#include <kytea/corpus-io.h>
#include <kytea/corpus-io-full.h>

#include <cstdlib>
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>

using namespace kytea;

static int failures = 0;

#define CHECK(cond, msg)                                              \
    do {                                                              \
        if (!(cond)) {                                                \
            std::cerr << "FAIL: " << msg << std::endl;                \
            failures++;                                               \
        }                                                             \
    } while (0)

int main() {
    // 1) StringUtilUtf8 character-type mapping (upstream TestKytea::testTypeString)
    {
        StringUtilUtf8 util;
        KyteaString str = util.mapString("漢カひ。１A");
        std::string act = util.getTypeString(str);
        CHECK(act == "KTHODR",
              "getTypeString(漢カひ。１A) == KTHODR, got " << act);
        // round-trip
        std::string rt = util.showString(str);
        CHECK(rt == "漢カひ。１A", "showString round-trip, got " << rt);
    }

    // 2) FullCorpusIO: parse a full-format tagged sentence
    {
        StringUtilUtf8 util;
        std::stringstream ss;
        ss << "京都/名詞/きょうと に/助詞/に 行/動詞/い っ/語尾/っ た/助動詞/た\n";
        FullCorpusIO io(&util, ss, false);
        KyteaSentence *sentence = io.readSentence();
        CHECK(sentence != 0, "readSentence returned a sentence");
        CHECK(sentence->words.size() == 5,
              "expected 5 words, got " << sentence->words.size());
        CHECK(util.showString(sentence->words[0].surface) == "京都",
              "first word should be 京都");
        CHECK(util.showString(sentence->words[0].getTagSurf(0)) == "名詞",
              "first tag(0) should be 名詞");
        CHECK(util.showString(sentence->words[0].getTagSurf(1)) == "きょうと",
              "first tag(1) should be きょうと");
        delete sentence;
    }

    // 3) Train a tiny model (same invocation style as upstream TestAnalysis)
    //    then run word-segmentation prediction on the trained text.
    {
        std::stringstream corpus_ss;
        corpus_ss << "これ/代名詞/これ は/助詞/は 学習/名詞/がくしゅう データ/名詞/でーた\n"
                  << "\n"
                  << "どうぞ/副詞/どうぞ モデル/名詞/もでる を/助詞/を 学習/名詞/がくしゅう し/動詞/し て/助詞/て\n"
                  << "京都/名詞/きょうと に/助詞/に 行/動詞/い っ/語尾/っ た/助動詞/た\n";
        const char* cmd[7] = {"", "-model", "/dev/null",
                              "-full", "-", "-global", "1"};
        // write corpus to a temp file (FullCorpusIO takes a filename)
        const char *tmpdir = getenv("TMPDIR");
        std::string corpus_file = std::string(tmpdir && *tmpdir ? tmpdir : "/tmp")
                                  + "/kytea-consumer-corpus.txt";
        {
            std::ofstream ofs(corpus_file.c_str());
            ofs << corpus_ss.str();
        }
        cmd[4] = corpus_file.c_str();

        KyteaConfig *config = new KyteaConfig;
        config->setDebug(0);
        config->setOnTraining(true);
        config->parseTrainCommandLine(7, cmd);
        Kytea *kytea = new Kytea(config);
        kytea->trainAll();
        StringUtil *util = kytea->getStringUtil();

        // predict segmentation on trained sentence "京都 に 行 っ た"
        KyteaString raw = util->mapString("京都に行った");
        KyteaSentence sent(raw, util->normalize(raw));
        kytea->calculateWS(sent);
        CHECK(sent.words.size() == 5,
              "calculateWS(京都に行った) -> 5 words, got " << sent.words.size());
        if (sent.words.size() == 5) {
            CHECK(util->showString(sent.words[0].surface) == "京都",
                  "first segmented word should be 京都, got "
                      << util->showString(sent.words[0].surface));
        }
        delete kytea;   // ~Kytea() also deletes config_ (takes ownership)
    }

    if (failures == 0) {
        std::cout << "kytea lib consumer assertions: 8 passed" << std::endl;
        return 0;
    }
    std::cerr << failures << " assertion(s) failed" << std::endl;
    return 1;
}
