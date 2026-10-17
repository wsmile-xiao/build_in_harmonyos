#include <cstring>
#include <iostream>

#include <unicode/ucol.h>
#include <unicode/ustring.h>
#include <unicode/uversion.h>

namespace {

bool check(bool condition, const char* message) {
    if (!condition) {
        std::cerr << "FAIL: " << message << '\n';
    }
    return condition;
}

}  // namespace

int main() {
    UErrorCode status = U_ZERO_ERROR;
    UChar lower[16] = {};
    UChar upper[16] = {};

    u_strFromUTF8(lower, 16, nullptr, "resume", -1, &status);
    if (!check(U_SUCCESS(status), "UTF-8 conversion failed")) {
        return 1;
    }

    UCollator* collator = ucol_open("en_US", &status);
    if (!check(U_SUCCESS(status) && collator != nullptr, "collator creation failed")) {
        return 1;
    }

    UChar later[16] = {};
    u_strFromUTF8(later, 16, nullptr, "zebra", -1, &status);
    bool ok = check(U_SUCCESS(status), "second UTF-8 conversion failed");
    ok = check(
             ucol_strcoll(collator, lower, -1, later, -1) == UCOL_LESS,
             "collation order is incorrect") &&
         ok;
    ucol_close(collator);

    u_strToUpper(upper, 16, lower, -1, "en_US", &status);
    ok = check(U_SUCCESS(status), "case conversion failed") && ok;
    UChar expected[16] = {};
    u_strFromUTF8(expected, 16, nullptr, "RESUME", -1, &status);
    ok = check(U_SUCCESS(status) &&
                   u_strcmpCodePointOrder(upper, expected) == 0,
               "uppercase result is incorrect") &&
         ok;
    ok = check(std::strncmp(U_ICU_VERSION, "77.", 3) == 0,
               "unexpected ICU version") &&
         ok;

    if (!ok) {
        return 1;
    }
    std::cout << "PASS: icu4c conversion, collation, casing, and version checks\n";
    return 0;
}
