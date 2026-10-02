#include <cstdlib>
#include <fstream>
#include <iostream>
#include <string>

#if defined(__OHOS__)
#include <sys/utsname.h>
#endif

namespace {

int fail(const std::string &message) {
    std::cerr << "FAIL: " << message << '\n';
    return 1;
}

}  // namespace

int main(int argc, char **argv) {
    bool require_ohos = false;
    std::string expected_machine;
    std::size_t expected_count = 56329;

    for (int index = 1; index < argc; ++index) {
        const std::string argument(argv[index]);
        if (argument == "--require-ohos") {
            require_ohos = true;
        } else if (argument.rfind("--expect-machine=", 0) == 0) {
            expected_machine = argument.substr(17);
        } else if (argument.rfind("--expect-count=", 0) == 0) {
            expected_count = static_cast<std::size_t>(
                std::stoull(argument.substr(15)));
        } else {
            return fail("unknown argument: " + argument);
        }
    }

    const char *path = std::getenv("WORDS_ES_FILE");
    if (path == nullptr || *path == '\0') {
        return fail("WORDS_ES_FILE is not set by the Conan package");
    }

    std::ifstream input(path, std::ios::binary);
    if (!input) {
        return fail("cannot open packaged word list: " + std::string(path));
    }

    std::size_t count = 0;
    bool has_hola = false;
    bool has_ano = false;
    bool has_espanol = false;
    bool has_arbol = false;
    std::string previous;
    std::string word;
    while (std::getline(input, word)) {
        if (word.empty()) {
            return fail("word list contains an empty record");
        }
        if (word.find('/') != std::string::npos) {
            return fail("Aspell affix metadata was not removed");
        }
        if (!previous.empty() && word <= previous) {
            return fail("word list is not strictly sorted and unique");
        }
        has_hola = has_hola || word == "hola";
        has_ano = has_ano || word == "a\xc3\xb1o";
        has_espanol = has_espanol || word == "espa\xc3\xb1ol";
        has_arbol = has_arbol || word == "\xc3\xa1rbol";
        previous = word;
        ++count;
    }
    if (!input.eof()) {
        return fail("failed while reading the word list");
    }
    if (count != expected_count) {
        return fail("unexpected word count: " + std::to_string(count));
    }
    if (!has_hola || !has_ano || !has_espanol || !has_arbol) {
        return fail("Spanish UTF-8 sample words are missing");
    }

    if (require_ohos) {
#if defined(__OHOS__)
        struct utsname system_info {};
        if (uname(&system_info) != 0) {
            return fail("uname failed on the HarmonyOS runtime");
        }
        if (!expected_machine.empty() && expected_machine != system_info.machine) {
            return fail("unexpected HarmonyOS machine: " +
                        std::string(system_info.machine));
        }
        std::cout << "HARMONYOS_TEST_OK machine=" << system_info.machine
                  << " entries=" << count << '\n';
#else
        return fail("--require-ohos used by a non-HarmonyOS binary");
#endif
    } else {
        std::cout << "WORDS_ES_TEST_OK entries=" << count << '\n';
    }

    return 0;
}
