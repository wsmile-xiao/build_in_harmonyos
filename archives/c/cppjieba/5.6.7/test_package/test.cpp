#include <iostream>
#include <string>
#include <vector>

#include "cppjieba/Jieba.hpp"
#include "cppjieba/KeywordExtractor.hpp"
#include "cppjieba/MixSegment.hpp"

#ifndef CPPJIEBA_DICT_DIR
#define CPPJIEBA_DICT_DIR ""
#endif

static std::string DictPath(const char* file) {
    std::string dir(CPPJIEBA_DICT_DIR);
    if (!dir.empty() && dir.back() != '/' && dir.back() != '\\') {
#ifdef _WIN32
        dir += '\\';
#else
        dir += '/';
#endif
    }
    return dir + file;
}

static std::string JoinSlash(const std::vector<std::string>& words) {
    std::string out;
    for (size_t i = 0; i < words.size(); ++i) {
        if (i) {
            out += '/';
        }
        out += words[i];
    }
    return out;
}

int main() {
    int passed = 0;
    int failed = 0;

    const std::string dict = DictPath("jieba.dict.utf8");
    const std::string hmm = DictPath("hmm_model.utf8");
    const std::string user = DictPath("user.dict.utf8");
    const std::string idf = DictPath("idf.utf8");
    const std::string stop = DictPath("stop_words.utf8");

    // 1. MixSegment precise cut (real dict lookup + HMM).
    {
        cppjieba::MixSegment seg(dict, hmm);
        std::vector<std::string> words;
        seg.Cut("他来到了网易杭研大厦", words);
        std::string actual = JoinSlash(words);
        std::string expected = "他/来到/了/网易/杭研/大厦";
        if (actual == expected) {
            std::cout << "[PASS] MixSegment precise cut" << std::endl;
            ++passed;
        } else {
            std::cout << "[FAIL] MixSegment precise cut: got '" << actual << "'" << std::endl;
            ++failed;
        }
        std::cout << "Segmentation output: " << actual << std::endl;
    }

    // 2. Full Jieba object: search cut + user-word insertion.
    {
        cppjieba::Jieba jieba(dict, hmm, user, idf, stop);
        std::vector<std::string> words;
        jieba.Cut("男默女泪", words);
        std::string before = JoinSlash(words);
        bool ok_before = (before == "男默/女泪");
        bool inserted = jieba.InsertUserWord("男默女泪");
        jieba.Cut("男默女泪", words);
        std::string after = JoinSlash(words);
        bool ok_after = (after == "男默女泪");
        jieba.CutForSearch("他来到了网易杭研大厦", words);
        std::string search = JoinSlash(words);
        bool ok_search = (search == "他/来到/了/网易/杭研/大厦");
        if (ok_before && inserted && ok_after && ok_search) {
            std::cout << "[PASS] Jieba Cut/InsertUserWord/CutForSearch" << std::endl;
            ++passed;
        } else {
            std::cout << "[FAIL] Jieba: before='" << before << "' after='" << after
                      << "' search='" << search << "' inserted=" << inserted << std::endl;
            ++failed;
        }
    }

    // 3. Keyword extraction on a real sentence.
    {
        cppjieba::Jieba jieba(dict, hmm, user, idf, stop);
        std::string sentence =
            "我是拖拉机学院手扶拖拉机专业的。不用多久，我就会升职加薪，当上CEO，走上人生巅峰。";
        std::vector<cppjieba::KeywordExtractor::Word> kws;
        jieba.extractor.Extract(sentence, kws, 5);
        bool ok = (kws.size() == 5 && !kws[0].word.empty() && kws[0].weight > 0.0);
        bool has_ceo = false;
        for (size_t i = 0; i < kws.size(); ++i) {
            if (kws[i].word == "CEO") {
                has_ceo = true;
            }
        }
        if (ok && has_ceo) {
            std::cout << "[PASS] KeywordExtractor top5 contains CEO" << std::endl;
            ++passed;
        } else {
            std::cout << "[FAIL] KeywordExtractor: got " << kws.size() << " keywords";
            for (size_t i = 0; i < kws.size(); ++i) {
                std::cout << " [" << kws[i].word << ":" << kws[i].weight << "]";
            }
            std::cout << std::endl;
            ++failed;
        }
    }

    std::cout << "Summary: " << passed << "/3 passed" << std::endl;
    return failed == 0 ? 0 : 1;
}
