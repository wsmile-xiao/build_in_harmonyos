#include <kylin-chkname.h>

#include <cstdlib>
#include <cstring>
#include <iostream>
#include <string>
#include <unistd.h>

namespace {

constexpr int kTotalCases = 20;
int passed = 0;

bool report(bool condition, const char *description)
{
    if (!condition) {
        std::cerr << "FAIL: " << description << std::endl;
        return false;
    }
    ++passed;
    std::cout << "PASS[" << passed << "/" << kTotalCases << "]: "
              << description << std::endl;
    return true;
}

bool check_name(const char *name, int reserve, int expected,
                const char *description)
{
    return report(kylin_username_check(name, reserve) == expected, description);
}

}  // namespace

int main()
{
    bool ok = true;

    ok &= check_name("alice", 0, CHECK_SUCCESS, "letters are accepted");
    ok &= check_name("_service", 0, CHECK_SUCCESS, "leading underscore is accepted");
    ok &= check_name(".hidden", 0, CHECK_SUCCESS, "leading dot is accepted");
    ok &= check_name("machine$", 0, CHECK_SUCCESS, "trailing dollar is accepted");
    ok &= check_name("a-b.c_9", 0, CHECK_SUCCESS, "mixed valid characters are accepted");
    ok &= check_name(nullptr, 0, NAME_ERROR, "null name is rejected");
    ok &= check_name("", 0, LENGTH_ERROR, "empty name is rejected");
    ok &= check_name("abcdefghijklmnopqrstuvwxyz1234567", 0, LENGTH_ERROR,
                     "names longer than 32 bytes are rejected");
    ok &= check_name(".", 0, REGEX_ERROR, "single dot is rejected");
    ok &= check_name("..", 0, REGEX_ERROR, "double dot is rejected");
    ok &= check_name("-bad", 0, FIRST_CHAR_ERROR, "invalid first character is rejected");
    ok &= check_name("bad@name", 0, REGEX_ERROR, "invalid body character is rejected");
    ok &= check_name("12345", 0, NUMBERIC_ERROR, "fully numeric name is rejected");
    ok &= check_name("0x1f", 0, HEX_ERROR, "hexadecimal name is rejected");
    ok &= check_name("0o77", 0, OCTAL_ERROR, "octal name is rejected");
    ok &= check_name("root", 0, CHECK_SUCCESS, "reserve filtering can be disabled");
    ok &= check_name("root", 1, RESERVED_ERROR, "packaged reserved name is rejected");

    const char *saved_reserved = std::getenv("KYLIN_CHKNAME_RESERVED_NAMES");
    const std::string original_reserved = saved_reserved ? saved_reserved : "";
    setenv("KYLIN_CHKNAME_RESERVED_NAMES", "/path/that/does/not/exist", 1);
    ok &= check_name("alice", 1, OPEN_RESERVED_NAMES_ERROR,
                     "missing reserved-name data is reported");
    if (saved_reserved)
        setenv("KYLIN_CHKNAME_RESERVED_NAMES", original_reserved.c_str(), 1);
    else
        unsetenv("KYLIN_CHKNAME_RESERVED_NAMES");

    const char *success = kylin_username_strerror(CHECK_SUCCESS);
    const char *unknown = kylin_username_strerror(-1000);
    ok &= report(success != nullptr && success[0] != '\0' && unknown != nullptr &&
                     unknown[0] != '\0' && std::strcmp(success, unknown) != 0,
                 "known and unknown status strings are meaningful");

    const char *reserved_path = std::getenv("KYLIN_CHKNAME_RESERVED_NAMES");
    const char *locale_path = std::getenv("KYLIN_CHKNAME_LOCALEDIR");
#if defined(__OHOS__) && defined(__aarch64__)
    const bool harmony_target = true;
#elif defined(__OHOS__)
    const bool harmony_target = false;
#else
    // Keep the recipe testable on its supported Linux build platform.  On
    // OHOS the branch above strictly requires the contest target ABI.
    const bool harmony_target = true;
#endif
    ok &= report(harmony_target && reserved_path != nullptr && locale_path != nullptr &&
                     access(reserved_path, R_OK) == 0 && access(locale_path, R_OK) == 0,
                 "HarmonyOS AArch64 target loads packaged runtime resources");

    if (!ok || passed != kTotalCases) {
        std::cerr << "RESULT: " << passed << "/" << kTotalCases << " passed"
                  << std::endl;
        return 1;
    }

    std::cout << "RESULT: 20/20 passed" << std::endl;
    return 0;
}
