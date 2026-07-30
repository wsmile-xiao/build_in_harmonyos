#include <cstdlib>
#include <fstream>
#include <iostream>
#include <set>
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
        std::ifstream missing(join(argv[2], "ca.dic").c_str());
        if (missing.is_open())
        {
            std::cerr << "fault directory unexpectedly contains a dictionary\n";
            return 1;
        }
        std::cout << "missing Catalan dictionary directory rejected\n";
        return 0;
    }
    if (argc != 2)
    {
        std::cerr << "usage: test_hunspell_ca <dictionary-directory>\n";
        return 2;
    }

    const std::string root = argv[1];
    const char* locales[] = {"ca", "ca_ES", "ca_ES-valencia"};
    std::vector<std::set<std::string> > dictionaries(3);
    for (int index = 0; index != 3; ++index)
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

    if (dictionaries[0] != dictionaries[1])
    {
        std::cerr << "ca and ca_ES aliases differ\n";
        return 5;
    }
    if (dictionaries[0].count("Catalunya") != 1 ||
        dictionaries[0].count("Barcelona") != 1 ||
        dictionaries[0].count("ordinador") != 1)
    {
        std::cerr << "representative Catalan entries are absent\n";
        return 6;
    }
    if (dictionaries[2].count("València") != 1 ||
        dictionaries[2].count("ordinador") != 1)
    {
        std::cerr << "representative Valencian entries are absent\n";
        return 7;
    }
    if (dictionaries[0].count("CodexDefinitelyNotAWord") != 0)
    {
        std::cerr << "negative dictionary lookup unexpectedly matched\n";
        return 8;
    }

    std::cout << "hunspell-ca semantic checks passed\n";
    return 0;
}
