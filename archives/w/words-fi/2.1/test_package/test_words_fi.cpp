#include <algorithm>
#include <cerrno>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <set>
#include <string>
#include <vector>

#if defined(__OHOS__)
#include <sys/utsname.h>
#endif

namespace {

std::vector<unsigned char> dictionary_key(const std::string& word)
{
    std::vector<unsigned char> key;
    for (unsigned char byte : word) {
        if (byte == 32 || (byte >= '0' && byte <= '9') ||
            (byte >= 'A' && byte <= 'Z') || (byte >= 'a' && byte <= 'z')) {
            if (byte >= 'A' && byte <= 'Z')
                byte = static_cast<unsigned char>(byte + ('a' - 'A'));
            key.push_back(byte);
        }
    }
    return key;
}

bool bytewise_less(const std::string& left, const std::string& right)
{
    return std::lexicographical_compare(
        left.begin(), left.end(), right.begin(), right.end(),
        [](char a, char b) {
            return static_cast<unsigned char>(a) < static_cast<unsigned char>(b);
        });
}

struct WordLess {
    bool operator()(const std::string& left, const std::string& right) const
    {
        const auto left_key = dictionary_key(left);
        const auto right_key = dictionary_key(right);
        if (left_key != right_key)
            return left_key < right_key;
        return bytewise_less(left, right);
    }
};

bool is_continuation(unsigned char byte)
{
    return byte >= 0x80 && byte <= 0xbf;
}

bool valid_utf8(const std::string& value)
{
    std::size_t index = 0;
    while (index < value.size()) {
        const auto first = static_cast<unsigned char>(value[index]);
        if (first <= 0x7f) {
            ++index;
            continue;
        }
        if (first >= 0xc2 && first <= 0xdf) {
            if (index + 1 >= value.size() ||
                !is_continuation(static_cast<unsigned char>(value[index + 1])))
                return false;
            index += 2;
            continue;
        }
        if (first >= 0xe0 && first <= 0xef) {
            if (index + 2 >= value.size())
                return false;
            const auto second = static_cast<unsigned char>(value[index + 1]);
            const auto third = static_cast<unsigned char>(value[index + 2]);
            if (!is_continuation(third))
                return false;
            if (first == 0xe0) {
                if (second < 0xa0 || second > 0xbf)
                    return false;
            } else if (first == 0xed) {
                if (second < 0x80 || second > 0x9f)
                    return false;
            } else if (!is_continuation(second)) {
                return false;
            }
            index += 3;
            continue;
        }
        if (first >= 0xf0 && first <= 0xf4) {
            if (index + 3 >= value.size())
                return false;
            const auto second = static_cast<unsigned char>(value[index + 1]);
            if (!is_continuation(static_cast<unsigned char>(value[index + 2])) ||
                !is_continuation(static_cast<unsigned char>(value[index + 3])))
                return false;
            if (first == 0xf0) {
                if (second < 0x90 || second > 0xbf)
                    return false;
            } else if (first == 0xf4) {
                if (second < 0x80 || second > 0x8f)
                    return false;
            } else if (!is_continuation(second)) {
                return false;
            }
            index += 4;
            continue;
        }
        return false;
    }
    return true;
}

bool contains(const std::vector<std::string>& words, const std::string& word)
{
    return std::binary_search(words.begin(), words.end(), word, WordLess{});
}

int fail(int code, const std::string& message)
{
    std::cerr << message << '\n';
    return code;
}

} // namespace

int main(int argc, char** argv)
{
    std::string word_file;
    if (const char* value = std::getenv("WORDS_FI_FILE"))
        word_file = value;
    std::size_t expected_count = 88328;
    bool expect_missing = false;
    bool require_ohos = false;
    std::string expected_machine;

    for (int index = 1; index < argc; ++index) {
        const std::string argument(argv[index]);
        const std::string path_option = "--word-list=";
        const std::string count_option = "--expect-count=";
        const std::string machine_option = "--expect-machine=";
        if (argument.rfind(path_option, 0) == 0) {
            word_file = argument.substr(path_option.size());
        } else if (argument.rfind(count_option, 0) == 0) {
            const auto text = argument.substr(count_option.size());
            char* end = nullptr;
            errno = 0;
            const auto parsed = std::strtoull(text.c_str(), &end, 10);
            if (text.empty() || errno != 0 || end == text.c_str() || *end != '\0')
                return fail(2, "invalid --expect-count value");
            expected_count = static_cast<std::size_t>(parsed);
        } else if (argument == "--expect-missing") {
            expect_missing = true;
        } else if (argument == "--require-ohos") {
            require_ohos = true;
        } else if (argument.rfind(machine_option, 0) == 0) {
            expected_machine = argument.substr(machine_option.size());
        } else {
            return fail(2, "unknown argument: " + argument);
        }
    }

    if (!expected_machine.empty() && !require_ohos)
        return fail(2, "--expect-machine requires --require-ohos");
    if (word_file.empty())
        return fail(2, "WORDS_FI_FILE is unset and --word-list was not provided");

    if (expect_missing) {
        std::ifstream missing(word_file, std::ios::binary);
        if (missing.is_open())
            return fail(1, "fault path unexpectedly opened");
        std::cout << "missing word-list path rejected\n";
        return 0;
    }

    std::string machine;
    if (require_ohos) {
#if !defined(__OHOS__)
        return fail(10, "--require-ohos rejected: binary was not compiled for HarmonyOS");
#else
        struct utsname details {};
        if (uname(&details) != 0)
            return fail(11, "uname failed on HarmonyOS");
        machine = details.machine;
        if (!expected_machine.empty() && machine != expected_machine)
            return fail(12, "unexpected HarmonyOS machine: " + machine);
#endif
    }

    std::ifstream input(word_file, std::ios::binary);
    if (!input)
        return fail(3, "cannot open packaged Finnish word list");

    std::vector<std::string> words;
    std::set<std::string> unique_words;
    std::string line;
    while (std::getline(input, line)) {
        if (!line.empty() && line.back() == '\r')
            line.pop_back();
        if (line.empty())
            return fail(4, "word list contains an empty entry");
        if (!valid_utf8(line))
            return fail(5, "word list contains invalid RFC 3629 UTF-8");
        if (line.find('/') != std::string::npos)
            return fail(6, "word list contains Aspell slash metadata");
        if (!words.empty() && !WordLess{}(words.back(), line))
            return fail(7, "word list is not strictly sorted by the package dictionary key");
        if (!unique_words.insert(line).second)
            return fail(8, "word list contains duplicates");
        words.push_back(line);
    }
    if (input.bad())
        return fail(9, "error while reading Finnish word list");
    if (words.size() != expected_count)
        return fail(13, "unexpected Finnish word count: " + std::to_string(words.size()));

    const std::vector<std::string> required_words = {"j\xc3\xa4rvi", "y\xc3\xb6", "\xc3\xa4\xc3\xa4ni", "kaunis"};
    for (const auto& sample : required_words) {
        if (!contains(words, sample))
            return fail(14, "required Finnish sample is absent: " + sample);
    }
    if (contains(words, "CodexDefinitelyNotAWord"))
        return fail(15, "negative lookup unexpectedly matched");

    if (require_ohos) {
        std::cout << "HARMONYOS_TEST_OK entries=" << words.size()
                  << " machine=" << machine << '\n';
    } else {
        std::cout << "WORDS_FI_TEST_OK entries=" << words.size() << '\n';
    }
    return 0;
}
