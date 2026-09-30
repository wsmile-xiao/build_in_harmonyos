#include <algorithm>
#include <fstream>
#include <iostream>
#include <string>
#if defined(__OHOS__)
#include <sys/utsname.h>
#endif
#include <vector>

static bool contains(const std::vector<std::string>& words, const std::string& word)
{
    return std::binary_search(words.begin(), words.end(), word);
}

static bool load_words(const std::string& path, std::vector<std::string>& words)
{
    std::ifstream input(path.c_str(), std::ios::binary);
    if (!input)
        return false;

    std::string line;
    while (std::getline(input, line))
    {
        if (!line.empty() && line.back() == '\r')
            line.pop_back();
        if (!line.empty())
            words.push_back(line);
    }
    return input.eof();
}

static bool validate_dictionary(const std::string& path, std::size_t expected_count,
                                const std::string& required, const std::string& forbidden)
{
    std::vector<std::string> words;
    if (!load_words(path, words))
    {
        std::cerr << "cannot read dictionary: " << path << "\n";
        return false;
    }
    if (words.size() != expected_count)
    {
        std::cerr << "unexpected entry count in " << path << ": " << words.size() << "\n";
        return false;
    }
    if (!std::is_sorted(words.begin(), words.end()))
    {
        std::cerr << "dictionary is not bytewise sorted: " << path << "\n";
        return false;
    }
    if (std::adjacent_find(words.begin(), words.end()) != words.end())
    {
        std::cerr << "dictionary contains duplicate entries: " << path << "\n";
        return false;
    }
    if (!contains(words, required) || contains(words, forbidden))
    {
        std::cerr << "expected German spelling distinction failed in " << path << "\n";
        return false;
    }
    return true;
}

int main(int argc, char** argv)
{
    if (argc == 3 && std::string(argv[1]) == "--expect-missing")
    {
        std::ifstream missing(argv[2], std::ios::binary);
        if (missing.is_open())
        {
            std::cerr << "fault path unexpectedly opened\n";
            return 1;
        }
        std::cout << "missing dictionary path rejected\n";
        return 0;
    }

    const bool harmonyos_runtime = argc == 3 && std::string(argv[1]) == "--harmonyos-runtime";
    if (!harmonyos_runtime && argc != 2)
    {
        std::cerr << "usage: test_words_de [--harmonyos-runtime] <dictionary-directory>\n";
        return 2;
    }
    if (harmonyos_runtime)
    {
#if !defined(__OHOS__)
        std::cerr << "consumer was not compiled for the HarmonyOS target\n";
        return 3;
#else
        struct utsname system_info;
        if (uname(&system_info) != 0 || std::string(system_info.machine) != "x86_64")
        {
            std::cerr << "HarmonyOS PC runtime is not x86_64\n";
            return 4;
        }
#endif
    }

    const std::string directory = argv[argc - 1];
    const std::string new_spelling = directory + "/ngerman";
    const std::string old_spelling = directory + "/ogerman";
    const std::string alias = directory + "/german";
    if (!validate_dictionary(new_spelling, 304736, "dass", "da\xC3\x9F"))
        return 5;
    if (!validate_dictionary(old_spelling, 76258, "da\xC3\x9F", "dass"))
        return 6;

    std::vector<std::string> new_words;
    std::vector<std::string> alias_words;
    if (!load_words(new_spelling, new_words) || !load_words(alias, alias_words) ||
        new_words != alias_words)
    {
        std::cerr << "german alias does not match ngerman\n";
        return 7;
    }
    if (!harmonyos_runtime && (!contains(new_words, "Schifffahrt") ||
                               !contains(alias_words, "Stra\xC3\x9F" "e")))
    {
        std::cerr << "modern German UTF-8 samples are absent\n";
        return 8;
    }
    if (!harmonyos_runtime)
        std::cout << "words-de dictionaries passed consumer checks\n";
    else
        std::cout << "words-de HarmonyOS x86_64 runtime check passed\n";
    return 0;
}
