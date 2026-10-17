#include <cstdlib>
#include <cstring>
#include <string>
int main(int argc, char **argv) {
    if (argc < 2 || argv[1] == nullptr || argv[1][0] == 0)
        return EXIT_FAILURE;
    const std::string command = std::string("\"") + argv[1] + "\" --help";
    return std::system(command.c_str()) == 0 ? EXIT_SUCCESS : EXIT_FAILURE;
}
