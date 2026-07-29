#include <cstdlib>
#include <fstream>
#include <iostream>
#include <set>
#include <sstream>
#include <string>
#include <vector>

static std::string join(const std::string& root, const std::string& file)
{
    const char separator =
#ifdef _WIN32
        '\\';
#else
        '/';
#endif
    return root + separator + file;
}

static bool load_dictionary(const std::string& path, std::set<std::string>& words)
{
    std::ifstream input(path.c_str());
    if (!input)
        return false;

    std::string first;
    if (!std::getline(input, first))
        return false;
    const long declared = std::strtol(first.c_str(), 0, 10);
    if (declared <= 0)
        return false;

    std::string line;
    long actual = 0;
    while (std::getline(input, line))
    {
        if (!line.empty() && line.back() == '\r')
            line.pop_back();
        const std::string::size_type slash = line.find('/');
        words.insert(line.substr(0, slash));
        ++actual;
    }
    return actual == declared;
}

static bool affix_is_utf8(const std::string& path)
{
    std::ifstream input(path.c_str());
    std::string line;
    while (std::getline(input, line))
    {
        if (line == "SET UTF-8" || line == "SET UTF-8\r")
            return true;
    }
    return false;
}

int main(int argc, char** argv)
{
    if (argc == 3 && std::string(argv[1]) == "--expect-missing")
    {
        std::ifstream missing(join(argv[2], "en_US.dic").c_str());
        if (missing.is_open())
        {
            std::cerr << "fault directory unexpectedly contains a dictionary\n";
            return 1;
        }
        std::cout << "missing dictionary directory rejected\n";
        return 0;
    }
    if (argc != 2)
    {
        std::cerr << "usage: test_hunspell_en <dictionary-directory>\n";
        return 2;
    }

    const std::string root = argv[1];
    const char* locales[] = {
        "en_US", "en_CA", "en_AU", "en_GB-ise", "en_GB-ize", "en_GB"
    };
    std::vector<std::set<std::string> > dictionaries(6);
    for (int index = 0; index != 6; ++index)
    {
        const std::string locale = locales[index];
        if (!affix_is_utf8(join(root, locale + ".aff")))
        {
            std::cerr << locale << " does not declare UTF-8\n";
            return 3;
        }
        if (!load_dictionary(join(root, locale + ".dic"), dictionaries[index]))
        {
            std::cerr << locale << " has an invalid declared entry count\n";
            return 4;
        }
    }

    if (dictionaries[0].count("color") != 1 ||
        dictionaries[0].count("colour") != 0)
    {
        std::cerr << "US dialect spelling check failed\n";
        return 5;
    }
    if (dictionaries[3].count("colour") != 1 ||
        dictionaries[3].count("organise") != 1)
    {
        std::cerr << "British -ise dialect spelling check failed\n";
        return 6;
    }
    if (dictionaries[4].count("colour") != 1 ||
        dictionaries[4].count("organize") != 1)
    {
        std::cerr << "British -ize dialect spelling check failed\n";
        return 7;
    }
    if (dictionaries[5] != dictionaries[3])
    {
        std::cerr << "en_GB alias differs from en_GB-ise\n";
        return 8;
    }
    if (dictionaries[0].count("CodexDefinitelyNotAWord") != 0)
    {
        std::cerr << "negative dictionary lookup unexpectedly matched\n";
        return 9;
    }

    std::cout << "hunspell-en semantic checks passed\n";
    return 0;
}
