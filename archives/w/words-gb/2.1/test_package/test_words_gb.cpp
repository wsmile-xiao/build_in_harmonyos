#include <algorithm>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>

static bool contains(const std::vector<std::string>& words, const std::string& word)
{
    return std::binary_search(words.begin(), words.end(), word);
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
        std::cout << "missing word-list path rejected\n";
        return 0;
    }

    if (argc != 2)
    {
        std::cerr << "usage: test_words_gb <word-list>\n";
        return 2;
    }

    std::ifstream input(argv[1], std::ios::binary);
    if (!input)
    {
        std::cerr << "cannot open packaged word list\n";
        return 3;
    }

    std::vector<std::string> words;
    std::string line;
    while (std::getline(input, line))
    {
        if (!line.empty() && line.back() == '\r')
            line.pop_back();
        if (!line.empty())
            words.push_back(line);
    }

    if (words.size() != 127466)
    {
        std::cerr << "unexpected entry count: " << words.size() << "\n";
        return 4;
    }
    if (!std::is_sorted(words.begin(), words.end()))
    {
        std::cerr << "word list is not sorted\n";
        return 5;
    }
    if (std::adjacent_find(words.begin(), words.end()) != words.end())
    {
        std::cerr << "word list contains duplicates\n";
        return 6;
    }
    if (!contains(words, "colour") || !contains(words, "centre") ||
        !contains(words, "whilst"))
    {
        std::cerr << "expected British spelling is absent\n";
        return 7;
    }
    if (contains(words, "color") || contains(words, "center"))
    {
        std::cerr << "American-only spelling leaked into words-gb\n";
        return 8;
    }
    if (contains(words, "CodexDefinitelyNotAWord"))
    {
        std::cerr << "negative lookup unexpectedly matched\n";
        return 9;
    }

    std::cout << "words-gb semantic checks passed\n";
    return 0;
}
