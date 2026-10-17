#include <fstream>
#include <iostream>
#include <string>

int main(int argc, char** argv)
{
    if (argc != 3)
    {
        std::cerr << "usage: test_words_native <dictionary-file> <word>\n";
        return 2;
    }

    std::ifstream input(argv[1], std::ios::binary);
    if (!input)
    {
        std::cerr << "cannot open dictionary file\n";
        return 3;
    }

    const std::string expected(argv[2]);
    std::string line;
    while (std::getline(input, line))
    {
        if (!line.empty() && line.back() == '\r')
            line.pop_back();
        if (line.find('/') != std::string::npos)
        {
            std::cerr << "Aspell flags remain in the installed data\n";
            return 4;
        }
        if (line == expected)
        {
            std::cout << "found " << expected << " in " << argv[1] << '\n';
            return 0;
        }
    }

    std::cerr << "expected word is absent: " << expected << '\n';
    return 5;
}
