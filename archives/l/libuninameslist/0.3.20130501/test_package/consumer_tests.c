/* Consumer-side contract tests for the installed libuninameslist
 * 0.3.20130501 package.
 *
 * libuninameslist exposes three functions (uninameslist.h):
 *   uniNamesList_name(unsigned long uni)  - official Unicode name
 *   uniNamesList_annot(unsigned long uni) - NamesList.txt annotations
 *   uniNamesList_NamesListVersion(void)   - data version banner
 *
 * The library is a pure data table + lookup: the consumer contract is
 * "correct name/annotation strings for representative code points across
 * the ASCII, Latin and Greek ranges; table-accurate NULL behaviour for
 * the ranges NamesList.txt leaves un-named (CJK Unified Ideographs,
 * Private Use Area); plus stable out-of-range handling".  Each numbered
 * CHECK prints a PASS line and is tallied at the end, which the CI L1
 * gate parses.
 */
#include <uninameslist.h>

#include <stdio.h>
#include <string.h>

static int g_checks = 0;
#define CHECK(cond, msg)                                       \
    do {                                                       \
        if (cond) {                                            \
            g_checks++;                                        \
            printf("[CHECK %02d] PASS: %s\n", g_checks, msg);  \
        } else {                                               \
            printf("[CHECK %02d] FAIL: %s\n", g_checks, msg);  \
            return 1;                                          \
        }                                                      \
    } while (0)

int main(void)
{
    /* --- 1. Version banner ----------------------------------------- */
    const char *ver = uniNamesList_NamesListVersion();
    CHECK(ver != NULL, "NamesListVersion returns non-NULL");
    CHECK(strstr(ver, "6.2") != NULL,
          "NamesListVersion banner carries NamesList.txt 6.2 stamp");

    /* --- 2. ASCII range official names ----------------------------- */
    CHECK(strcmp(uniNamesList_name(41), "RIGHT PARENTHESIS") == 0,
          "name(0x29) == RIGHT PARENTHESIS");
    CHECK(strcmp(uniNamesList_name(65), "LATIN CAPITAL LETTER A") == 0,
          "name(0x41) == LATIN CAPITAL LETTER A");
    CHECK(strcmp(uniNamesList_name(48), "DIGIT ZERO") == 0,
          "name(0x30) == DIGIT ZERO");

    /* --- 3. Latin-1 supplement ------------------------------------- */
    CHECK(strcmp(uniNamesList_name(0xE9), "LATIN SMALL LETTER E WITH ACUTE")
              == 0,
          "name(0xE9) == LATIN SMALL LETTER E WITH ACUTE");

    /* --- 4. Greek block -------------------------------------------- */
    /* NB: upstream data uses the official Unicode 6.2 spelling "LAMDA". */
    CHECK(strcmp(uniNamesList_name(0x3BB), "GREEK SMALL LETTER LAMDA") == 0,
          "name(0x3BB) == GREEK SMALL LETTER LAMDA");

    /* --- 5. Annotations --------------------------------------------- */
    const char *annot = uniNamesList_annot(0x3BB);
    CHECK(annot != NULL, "annot(0x3BB) returns non-NULL");
    CHECK(strstr(annot, "lambda") != NULL,
          "annot(0x3BB) cross-references lambda");

    const char *annot_ff = uniNamesList_annot(0xFF);
    CHECK(annot_ff != NULL, "annot(0xFF) returns non-NULL");
    CHECK(strstr(annot_ff, "latin") != NULL,
          "annot(0xFF) cross-references the latin small letter y");

    /* --- 6. CJK radicals + unihan: table-accurate coverage ------------- */
    /* Upstream 0.3.20130501 (Unicode 6.2 NamesList) carries per-character
     * names for CJK radicals and strokes but NOT for the 20k+ CJK Unified
     * Ideographs (U+4E00..U+9FFF are un-named in NamesList.txt: their
     * official names are algorithmic "CJK UNIFIED IDEOGRAPH-XXXX" and the
     * data table leaves them NULL), nor for the Private Use Area.  The
     * consumer contract therefore checks both sides of that boundary. */
    CHECK(strcmp(uniNamesList_name(0x2E80), "CJK RADICAL REPEAT") == 0,
          "name(0x2E80 CJK radical) == CJK RADICAL REPEAT");
    CHECK(uniNamesList_name(0x4E2D) == NULL,
          "name(0x4E2D CJK ideograph) is NULL (un-named in NamesList 6.2)");
    CHECK(uniNamesList_name(0xE000) == NULL,
          "name(0xE000 Private Use) is NULL (un-named in NamesList 6.2)");

    /* --- 7. Out-of-range code points ------------------------------- */
    /* 0x110000+ are outside Unicode: the 6.2-era table returns NULL or
     * a sentinel string; both are acceptable "no data" answers, a crash
     * or garbage pointer is not. */
    const char *oob = uniNamesList_name(0x110000);
    CHECK(oob == NULL || oob[0] == '\0',
          "name(0x110000 out of range) is NULL/empty, no garbage");
    oob = uniNamesList_name(0xFFFFFFFFUL);
    CHECK(oob == NULL || oob[0] == '\0',
          "name(0xFFFFFFFF out of range) is NULL/empty, no garbage");

    printf("CHECK passed: %d\n", g_checks);
    return 0;
}
