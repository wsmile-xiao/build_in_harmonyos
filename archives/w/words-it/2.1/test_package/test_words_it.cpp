#include <algorithm>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>

static bool contains(const std::vector<std::string>& words, const std::string& word)
{
    return std::binary_search(words.begin(), words.end(), word);
}

static int check(const char* name, bool passed)
{
    std::cout << (passed ? "PASS " : "FAIL ") << name << "\n";
    return passed ? 0 : 1;
}

int main(int argc, char** argv)
{
    if (argc == 3 && std::string(argv[1]) == "--expect-missing")
    {
        std::ifstream missing(argv[2], std::ios::binary);
        return check("missing word-list path is rejected", !missing.is_open());
    }

    if (argc != 1)
    {
        std::cerr << "usage: test_words_it [--expect-missing <path>]\n";
        return 2;
    }

    int failures = 0;
    const char* configured_path = std::getenv("WORDS_IT_FILE");
    failures += check("WORDS_IT_FILE is provided by the Conan run environment",
                      configured_path != nullptr && configured_path[0] != '\0');
    if (configured_path == nullptr || configured_path[0] == '\0')
        return failures;

    std::ifstream input(configured_path, std::ios::binary);
    failures += check("packaged Italian word list opens", input.is_open());
    if (!input)
        return failures;

    std::vector<std::string> words;
    std::string line;
    while (std::getline(input, line))
    {
        if (!line.empty() && line.back() == '\r')
            line.pop_back();
        if (!line.empty())
            words.push_back(line);
    }

    failures += check("word count is 92034", words.size() == 92034);
    failures += check("word list is bytewise sorted",
                      std::is_sorted(words.begin(), words.end()));
    failures += check("word list contains no duplicate entries",
                      std::adjacent_find(words.begin(), words.end()) == words.end());
    failures += check("Italian word ciao is present", contains(words, "ciao"));
    failures += check("Italian word bambino is present", contains(words, "bambino"));
    failures += check("UTF-8 spelling città is present",
                      contains(words, std::string("citt\xc3\xa0")));
    failures += check("UTF-8 spelling perché is present",
                      contains(words, std::string("perch\xc3\xa9")));
    failures += check("negative lookup is absent",
                      !contains(words, "CodexDefinitelyNotAWord"));

    return failures == 0 ? 0 : 1;
}
