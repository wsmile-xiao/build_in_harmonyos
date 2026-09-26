// Consumer test for icu4c 78.3 on OpenHarmony.
//
// Every assertion drives a data-backed ICU code path: the Unicode/CLDR payloads
// are embedded in libicudata.a by --with-data-packaging=static, so a passing run
// also proves the packaged library needs no runtime .dat lookup and no system
// ICU shared object.
#include <cstdio>
#include <cstring>
#include <string>

#include <unicode/ubrk.h>
#include <unicode/ucal.h>
#include <unicode/uclean.h>
#include <unicode/ucnv.h>
#include <unicode/ucol.h>
#include <unicode/uchar.h>
#include <unicode/icudataver.h>
#include <unicode/uloc.h>
#include <unicode/uregex.h>
#include <unicode/ustring.h>
#include <unicode/utypes.h>
#include <unicode/uversion.h>

namespace {

int g_total = 0;
int g_failed = 0;

void check(bool condition, const char* what) {
    ++g_total;
    if (condition) {
        std::printf("[PASS] %s\n", what);
    } else {
        std::printf("[FAIL] %s\n", what);
        ++g_failed;
    }
}

std::string toUtf8(const UChar* source, int32_t length) {
    UErrorCode status = U_ZERO_ERROR;
    char buffer[256] = {};
    u_strToUTF8(buffer, static_cast<int32_t>(sizeof(buffer)), nullptr, source, length,
                &status);
    return U_SUCCESS(status) ? std::string(buffer) : std::string();
}

int32_t fromUtf8(UChar* target, int32_t capacity, const char* source) {
    UErrorCode status = U_ZERO_ERROR;
    int32_t length = 0;
    u_strFromUTF8(target, capacity, &length, source, -1, &status);
    return U_SUCCESS(status) || status == U_STRING_NOT_TERMINATED_WARNING ? length : -1;
}

bool utf8Equals(const UChar* text, int32_t length, const char* expected) {
    return toUtf8(text, length) == expected;
}

bool versionIs(const UVersionInfo version, int major, int minor) {
    return version[0] == major && version[1] == minor;
}

// /proc/self/maps shows which libraries the process actually resolved.
bool noSharedIcuLoaded() {
    FILE* maps = std::fopen("/proc/self/maps", "r");
    if (maps == nullptr) {
        return false;
    }
    bool found = false;
    char line[1024] = {};
    while (std::fgets(line, static_cast<int>(sizeof(line)), maps) != nullptr) {
        if (std::strstr(line, "libicu") != nullptr) {
            found = true;
            break;
        }
    }
    std::fclose(maps);
    return !found;
}

}  // namespace

int main() {
    UErrorCode status = U_ZERO_ERROR;
    u_init(&status);
    check(U_SUCCESS(status), "u_init() succeeds against statically embedded ICU data");

    // --- identity: header macros, library version and data version must agree ---
    check(std::strcmp(U_ICU_VERSION, "78.3") == 0, "U_ICU_VERSION macro is 78.3");
    check(U_ICU_VERSION_MAJOR_NUM == 78 && U_ICU_VERSION_MINOR_NUM == 3,
          "version macros are 78.3");
    UVersionInfo library = {};
    u_getVersion(library);
    check(versionIs(library, 78, 3), "u_getVersion() reports 78.3");
    std::printf("       library version %d.%d.%d.%d\n", library[0], library[1], library[2],
                library[3]);

    UErrorCode data_status = U_ZERO_ERROR;
    UVersionInfo data = {};
    u_getDataVersion(data, &data_status);
    check(U_SUCCESS(data_status) && data[0] == 78,
          "u_getDataVersion() reads the packaged icuver data");
    std::printf("       data version %d.%d.%d.%d\n", data[0], data[1], data[2], data[3]);

    UVersionInfo unicode = {};
    u_getUnicodeVersion(unicode);
    check(unicode[0] >= 16, "u_getUnicodeVersion() reports a Unicode 16+ data set");
    std::printf("       Unicode version %d.%d.%d.%d\n", unicode[0], unicode[1], unicode[2],
                unicode[3]);

    // --- character properties from the packaged uprops data ---
    check(u_isalpha(0x0041) != 0 && u_isalpha(0x0061) != 0,
          "u_isalpha() accepts Latin letters");
    check(u_isalpha(0x0037) == 0, "u_isalpha() rejects a digit");
    check(u_isdigit(0x0037) != 0, "u_isdigit() accepts the same digit");
    check(u_charType(0x4E2D) == U_OTHER_LETTER,
          "u_charType() classifies a Han ideograph as Lo");
    check(u_charDirection(0x4E2D) == U_LEFT_TO_RIGHT,
          "u_charDirection() gives Han ideographs LTR bidi class");
    check(u_charDirection(0x0626) == U_RIGHT_TO_LEFT_ARABIC,
          "u_charDirection() gives an Arabic letter the AL bidi class");
    check(u_charDirection(0x0660) == U_ARABIC_NUMBER,
          "u_charDirection() gives Arabic-Indic digits the AN bidi class");
    std::printf("       U+0626=%d U+0660=%d (AL=%d AN=%d)\n", u_charDirection(0x0626),
                u_charDirection(0x0660), U_RIGHT_TO_LEFT_ARABIC, U_ARABIC_NUMBER);

    // --- error names ---
    check(std::strstr(u_errorName(U_BUFFER_OVERFLOW_ERROR), "BUFFER_OVERFLOW") != nullptr,
          "u_errorName() names U_BUFFER_OVERFLOW_ERROR");

    // --- UTF-8 / UTF-16 conversion of non-ASCII text ---
    const char* kanji = "\xe4\xb8\xad\xe6\x96\x87\xce\xa9";  // 中文Ω
    UChar text[16] = {};
    int32_t textLength = fromUtf8(text, 16, kanji);
    check(textLength == 3, "u_strFromUTF8() decodes 3 UTF-16 code units");
    check(utf8Equals(text, textLength, kanji), "u_strToUTF8() round-trips the same text");

    // --- locale-sensitive casing (needs CLDR special-casing data) ---
    UChar ascii[16] = {};
    int32_t asciiLength = fromUtf8(ascii, 16, "resume");
    UChar upper[16] = {};
    status = U_ZERO_ERROR;
    u_strToUpper(upper, 16, ascii, asciiLength, "en_US", &status);
    check(U_SUCCESS(status) && utf8Equals(upper, -1, "RESUME"),
          "u_strToUpper() uppercases ASCII");

    UChar dottedI[16] = {};
    UChar latinI[16] = {};
    fromUtf8(latinI, 16, "i");
    status = U_ZERO_ERROR;
    u_strToUpper(dottedI, 16, latinI, 1, "tr", &status);
    check(U_SUCCESS(status) && dottedI[0] == 0x0130,
          "u_strToUpper() applies Turkish special casing (U+0130)");
    std::printf("       Turkish upper(i) = U+%04X\n", dottedI[0]);

    // --- collation, including the numeric collation element table ---
    status = U_ZERO_ERROR;
    UCollator* collator = ucol_open("en_US", &status);
    check(U_SUCCESS(status) && collator != nullptr, "ucol_open(en_US) succeeds");
    if (collator != nullptr) {
        UChar zebra[16] = {};
        int32_t zebraLength = fromUtf8(zebra, 16, "zebra");
        check(ucol_strcoll(collator, ascii, asciiLength, zebra, zebraLength) == UCOL_LESS,
              "en_US collation orders resume before zebra");

        status = U_ZERO_ERROR;
        ucol_setAttribute(collator, UCOL_NUMERIC_COLLATION, UCOL_ON, &status);
        UChar item9[16] = {};
        UChar item10[16] = {};
        int32_t nineLength = fromUtf8(item9, 16, "item9");
        int32_t tenLength = fromUtf8(item10, 16, "item10");
        check(U_SUCCESS(status) &&
                  ucol_strcoll(collator, item9, nineLength, item10, tenLength) == UCOL_LESS,
              "numeric collation orders item9 before item10");
        ucol_close(collator);
    }

    // --- locale and CLDR display names ---
    char canonical[64] = {};
    status = U_ZERO_ERROR;
    uloc_canonicalize("en-US-posix", canonical, static_cast<int32_t>(sizeof(canonical)),
                      &status);
    check(U_SUCCESS(status) && std::strcmp(canonical, "en_US_POSIX") == 0,
          "uloc_canonicalize() normalises en-US-posix");
    std::printf("       canonical locale %s\n", canonical);

    UChar display[64] = {};
    status = U_ZERO_ERROR;
    int32_t displayLength = uloc_getDisplayLanguage("de", "en", display, 64, &status);
    check(U_SUCCESS(status) && toUtf8(display, displayLength) == "German",
          "uloc_getDisplayLanguage() reads CLDR display names");
    std::printf("       display name for de in en = %s\n",
                toUtf8(display, displayLength).c_str());

    // --- charset conversion data (GBK) ---
    char gbk[64] = {};
    status = U_ZERO_ERROR;
    int32_t gbkLength = ucnv_convert("GBK", "UTF-8", gbk, static_cast<int32_t>(sizeof(gbk)),
                                     kanji, -1, &status);
    check(U_SUCCESS(status) && gbkLength == 6, "ucnv_convert() maps UTF-8 to GBK bytes");
    char back[64] = {};
    status = U_ZERO_ERROR;
    ucnv_convert("UTF-8", "GBK", back, static_cast<int32_t>(sizeof(back)), gbk, gbkLength,
                 &status);
    check(U_SUCCESS(status) && std::strcmp(back, kanji) == 0,
          "ucnv_convert() maps the GBK bytes back to UTF-8");

    // --- break iteration rules (brkitr data) ---
    const char* flag = "\xf0\x9f\x87\xa9\xf0\x9f\x87\xaa";  // regional indicator pair
    UChar flagText[16] = {};
    int32_t flagLength = fromUtf8(flagText, 16, flag);
    check(flagLength == 4, "a two-scalar flag occupies 4 UTF-16 code units");
    status = U_ZERO_ERROR;
    UBreakIterator* breaks = ubrk_open(UBRK_CHARACTER, "en", flagText, flagLength, &status);
    check(U_SUCCESS(status) && breaks != nullptr, "ubrk_open() loads grapheme break rules");
    if (breaks != nullptr) {
        // ubrk_first() yields the boundary at offset 0, so clusters == boundaries
        // after 0. Verified positions: {0, 4} for this 4-code-unit text.
        int32_t graphemes = 0;
        std::string positions;
        for (int32_t boundary = ubrk_first(breaks); boundary != UBRK_DONE;
             boundary = ubrk_next(breaks)) {
            positions += std::to_string(boundary) + " ";
            if (boundary != 0) {
                ++graphemes;
            }
        }
        check(graphemes == 1, "one grapheme cluster for a two-scalar regional flag");
        std::printf("       grapheme boundary offsets: %s\n", positions.c_str());
        ubrk_close(breaks);
    }

    // --- regex with a Unicode property (i18n regex + property data) ---
    UChar pattern[32] = {};
    int32_t patternLength = fromUtf8(pattern, 32, "\\p{Han}+");
    status = U_ZERO_ERROR;
    URegularExpression* regex = uregex_open(pattern, patternLength, 0, nullptr, &status);
    check(U_SUCCESS(status) && regex != nullptr,
          "uregex_open() compiles a \\p{Han} pattern");
    if (regex != nullptr) {
        UChar han[16] = {};
        int32_t hanLength = fromUtf8(han, 16, "\xe4\xb8\xad\xe6\x96\x87" "abc");
        status = U_ZERO_ERROR;
        uregex_setText(regex, han, hanLength, &status);
        // uregex_find() searches the region; uregex_matches() only succeeds when
        // the whole region matches, so "中文abc" must be probed with find.
        UErrorCode find_status = U_ZERO_ERROR;
        bool found = uregex_find(regex, 0, &find_status) != 0 && U_SUCCESS(find_status);
        check(found, "uregex_find() locates a \\p{Han} run inside mixed text");
        if (found) {
            UErrorCode span_status = U_ZERO_ERROR;
            int32_t start = uregex_start(regex, 0, &span_status);
            int32_t end = uregex_end(regex, 0, &span_status);
            check(U_SUCCESS(span_status) && start == 0 && end == 2,
                  "the matched Han run covers exactly the two ideographs");
            std::printf("       matched span [%d,%d) of %d code units\n", start, end,
                        hanLength);
        }
        UChar only[16] = {};
        int32_t onlyLength = fromUtf8(only, 16, "\xe4\xb8\xad\xe6\x96\x87");
        status = U_ZERO_ERROR;
        uregex_setText(regex, only, onlyLength, &status);
        bool whole = false;
        if (U_SUCCESS(status)) {
            UErrorCode match_status = U_ZERO_ERROR;
            whole = uregex_matches(regex, 0, &match_status) != 0 &&
                    U_SUCCESS(match_status);
        }
        check(whole, "uregex_matches() accepts a Han-only region");
        uregex_close(regex);
    }

    // --- time zone data on a musl/OHOS root filesystem ---
    UChar zone[64] = {};
    status = U_ZERO_ERROR;
    int32_t zoneLength = ucal_getDefaultTimeZone(zone, 64, &status);
    std::string zoneName = toUtf8(zone, zoneLength);
    check(U_SUCCESS(status) && zoneLength > 0 && !zoneName.empty(),
          "ucal_getDefaultTimeZone() resolves a zone");
    std::printf("       default time zone %s\n", zoneName.c_str());

    status = U_ZERO_ERROR;
    const char* tz_version = ucal_getTZDataVersion(&status);
    check(tz_version != nullptr && tz_version[0] != '\0',
          "ucal_getTZDataVersion() reads the packaged tzdata");
    std::printf("       tzdata version %s\n", tz_version ? tz_version : "(null)");

    // --- HarmonyOS packaging contract: no runtime data path, no shared ICU ---
    u_setDataDirectory("/storage/Users/currentUser/definitely-not-icu-data");
    status = U_ZERO_ERROR;
    UCollator* post = ucol_open("fr_FR", &status);
    check(U_SUCCESS(status) && post != nullptr,
          "ICU still opens locale data after u_setDataDirectory() points nowhere");
    if (post != nullptr) {
        ucol_close(post);
    }
    check(noSharedIcuLoaded(), "process maps no libicu shared object (statically linked)");

    std::printf("TOTAL=%d PASS=%d FAIL=%d\n", g_total, g_total - g_failed, g_failed);
    if (g_failed != 0) {
        std::printf("SOME TESTS FAILED\n");
        return 1;
    }
    std::printf("ALL TESTS PASSED\n");
    return 0;
}
