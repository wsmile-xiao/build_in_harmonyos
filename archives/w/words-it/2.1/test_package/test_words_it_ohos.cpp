#if !defined(__OHOS__)
#error "This consumer test must be compiled for HarmonyOS"
#endif

#if !defined(__aarch64__)
#error "This consumer test must be compiled for AArch64"
#endif

#include <cstdlib>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>

static int check(const char* name, bool passed)
{
    std::cout << (passed ? "PASS " : "FAIL ") << name << "\n";
    return passed ? 0 : 1;
}

int main()
{
    int failures = 0;
    const char* configured_path = std::getenv("WORDS_IT_FILE");
    const bool has_path = configured_path != nullptr && configured_path[0] != '\0';
    failures += check("HarmonyOS run environment provides WORDS_IT_FILE", has_path);
    if (!has_path)
        return failures;

    const std::string path(configured_path);
    failures += check("HarmonyOS package path is absolute", path.front() == '/');

    std::ifstream input(path, std::ios::binary);
    failures += check("HarmonyOS opens the installed word list", input.is_open());
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

    failures += check("HarmonyOS reads all 92034 entries", words.size() == 92034);
    bool has_utf8_italian_word = false;
    for (const std::string& word : words)
    {
        if (word == std::string("citt\xc3\xa0"))
        {
            has_utf8_italian_word = true;
            break;
        }
    }
    failures += check("HarmonyOS preserves UTF-8 spelling città", has_utf8_italian_word);
    return failures == 0 ? 0 : 1;
}
