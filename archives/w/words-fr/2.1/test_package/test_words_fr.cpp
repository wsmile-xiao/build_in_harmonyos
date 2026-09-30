#include <algorithm>
#include <cerrno>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <string>
#include <sys/utsname.h>
#include <unordered_set>
#include <utility>
#include <vector>

#if defined(WORDS_FR_REQUIRE_OHOS) && !defined(__OHOS__)
#error "The HarmonyOS consumer must be compiled by the OHOS target toolchain"
#endif
#if defined(WORDS_FR_REQUIRE_AARCH64) && !defined(__aarch64__)
#error "The HarmonyOS consumer must target AArch64"
#endif

namespace {
using SortKey = std::pair<std::string, std::string>;

int compare_bytes(const std::string& left, const std::string& right) {
    const auto less = [](char a, char b) {
        return static_cast<unsigned char>(a) < static_cast<unsigned char>(b);
    };
    if (std::lexicographical_compare(left.begin(), left.end(), right.begin(), right.end(), less)) return -1;
    if (std::lexicographical_compare(right.begin(), right.end(), left.begin(), left.end(), less)) return 1;
    return 0;
}

SortKey sort_key(const std::string& word) {
    std::string primary;
    for (unsigned char value : word) {
        if (value == 32 || (value >= 48 && value <= 57) ||
            (value >= 65 && value <= 90) || (value >= 97 && value <= 122)) {
            primary.push_back(static_cast<char>(value >= 65 && value <= 90 ? value + 32 : value));
        }
    }
    return {primary, word};
}

bool key_less(const std::string& left, const std::string& right) {
    const auto left_key = sort_key(left);
    const auto right_key = sort_key(right);
    int cmp = compare_bytes(left_key.first, right_key.first);
    return cmp < 0 || (cmp == 0 && compare_bytes(left_key.second, right_key.second) < 0);
}

bool valid_utf8(const std::string& value) {
    const auto* bytes = reinterpret_cast<const unsigned char*>(value.data());
    std::size_t i = 0;
    while (i < value.size()) {
        unsigned char c = bytes[i++];
        if (c <= 0x7f) continue;
        if (c >= 0xc2 && c <= 0xdf) {
            if (i >= value.size() || (bytes[i++] & 0xc0) != 0x80) return false;
            continue;
        }
        if (c >= 0xe0 && c <= 0xef) {
            if (i + 1 >= value.size()) return false;
            unsigned char c1 = bytes[i++];
            unsigned char c2 = bytes[i++];
            if ((c1 & 0xc0) != 0x80 || (c2 & 0xc0) != 0x80) return false;
            if (c == 0xe0 && c1 < 0xa0) return false;
            if (c == 0xed && c1 >= 0xa0) return false;
            continue;
        }
        if (c >= 0xf0 && c <= 0xf4) {
            if (i + 2 >= value.size()) return false;
            unsigned char c1 = bytes[i++];
            unsigned char c2 = bytes[i++];
            unsigned char c3 = bytes[i++];
            if ((c1 & 0xc0) != 0x80 || (c2 & 0xc0) != 0x80 || (c3 & 0xc0) != 0x80) return false;
            if (c == 0xf0 && c1 < 0x90) return false;
            if (c == 0xf4 && c1 > 0x8f) return false;
            continue;
        }
        return false;
    }
    return true;
}

struct Options {
    std::string path;
    std::size_t expected_count = 629569;
    bool require_ohos = false;
    bool expect_missing = false;
    std::string expected_machine;
};

bool parse_options(int argc, char** argv, Options& options) {
    const char* env_path = std::getenv("WORDS_FR_FILE");
    if (env_path) options.path = env_path;
    for (int i = 1; i < argc; ++i) {
        std::string arg(argv[i]);
        if (arg.rfind("--word-list=", 0) == 0) {
            options.path = arg.substr(12);
        } else if (arg.rfind("--expect-count=", 0) == 0) {
            options.expected_count = static_cast<std::size_t>(std::strtoull(arg.substr(15).c_str(), nullptr, 10));
        } else if (arg == "--require-ohos") {
            options.require_ohos = true;
        } else if (arg == "--expect-missing") {
            options.expect_missing = true;
        } else if (arg.rfind("--expect-machine=", 0) == 0) {
            options.expected_machine = arg.substr(17);
        } else {
            std::cerr << "FAIL: unknown argument: " << arg << "\n";
            return false;
        }
    }
    if (options.path.empty() && !options.expect_missing) {
        std::cerr << "FAIL: WORDS_FR_FILE is unset and --word-list was not supplied\n";
        return false;
    }
    return true;
}
}  // namespace

int main(int argc, char** argv) {
    Options options;
    if (!parse_options(argc, argv, options)) return 2;

    struct utsname system_info {};
    if (uname(&system_info) != 0) {
        std::cerr << "FAIL: uname: " << errno << "\n";
        return 3;
    }
    if (options.require_ohos) {
#if !defined(__OHOS__)
        std::cerr << "FAIL: binary was not compiled for HarmonyOS\n";
        return 4;
#endif
    }
    if (!options.expected_machine.empty() && options.expected_machine != system_info.machine) {
        std::cerr << "FAIL: machine=" << system_info.machine
                  << " expected=" << options.expected_machine << "\n";
        return 5;
    }

    std::ifstream input(options.path, std::ios::binary);
    if (!input) {
        if (options.expect_missing) {
            std::cout << "EXPECTED_MISSING_PATH_REJECTED\n";
            return 0;
        }
        std::cerr << "FAIL: cannot open WORDS_FR_FILE=" << options.path << "\n";
        return 6;
    }
    if (options.expect_missing) {
        std::cerr << "FAIL: expected missing path but the consumer opened it\n";
        return 15;
    }

    std::vector<std::string> words;
    std::unordered_set<std::string> unique;
    std::string line;
    std::string previous;
    while (std::getline(input, line)) {
        if (line.empty() || line.find('/') != std::string::npos || line.find('\r') != std::string::npos) {
            std::cerr << "FAIL: blank word or unnormalized metadata in dictionary\n";
            return 7;
        }
        if (!valid_utf8(line)) {
            std::cerr << "FAIL: invalid UTF-8 word entry\n";
            return 8;
        }
        if (!previous.empty() && !key_less(previous, line)) {
            std::cerr << "FAIL: dictionary is not strictly sorted\n";
            return 9;
        }
        if (!unique.insert(line).second) {
            std::cerr << "FAIL: duplicate dictionary entry\n";
            return 10;
        }
        words.push_back(line);
        previous = line;
    }
    if (!input.eof() || words.size() != options.expected_count) {
        std::cerr << "FAIL: entries=" << words.size()
                  << " expected=" << options.expected_count << "\n";
        return 11;
    }

    for (const std::string& sample : {"bonjour", "français", "éclair", "été"}) {
        if (unique.find(sample) == unique.end()) {
            std::cerr << "FAIL: missing French word " << sample << "\n";
            return 12;
        }
    }
    if (unique.find("__words_fr_missing_test_marker__") != unique.end()) {
        std::cerr << "FAIL: negative lookup unexpectedly matched\n";
        return 13;
    }

#if defined(WORDS_FR_REQUIRE_AARCH64)
    if (std::string(system_info.machine) != "aarch64") {
        std::cerr << "FAIL: HarmonyOS AArch64 binary ran on " << system_info.machine << "\n";
        return 14;
    }
#endif

    std::cout << "WORDS_FR_HARMONY_OK entries=" << words.size()
              << " machine=" << system_info.machine << "\n";
    return 0;
}
