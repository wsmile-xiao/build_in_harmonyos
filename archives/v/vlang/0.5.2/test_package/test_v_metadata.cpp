#include <cstdlib>
#include <iostream>
#include <string>

static std::string quote_arg(const char *arg) {
    std::string quoted = "\"";
    for (const char *p = arg; *p != '\0'; ++p) {
        if (*p == '"' || *p == '\\') {
            quoted += '\\';
        }
        quoted += *p;
    }
    quoted += '"';
    return quoted;
}

int main(int argc, char **argv) {
    if (argc < 3) {
        std::cerr << "usage: test_v_metadata [launcher] <v-wrapper> version\n";
        return 1;
    }

    std::string command;
    for (int i = 1; i < argc; ++i) {
        if (!command.empty()) {
            command += ' ';
        }
        command += quote_arg(argv[i]);
    }

    std::cout << "running installed V wrapper: " << command << '\n';
    int result = std::system(command.c_str());
    if (result != 0) {
        std::cerr << "installed V wrapper failed with status " << result << '\n';
        return 1;
    }
    return 0;
}
