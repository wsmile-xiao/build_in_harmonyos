/* Consumer test for snowball 2.2.0 (libstemmer).
 *
 * All stem expectations were pinned from the release-dated verification run:
 * data snapshot snowball-data@0703f1d6a218 (last commit before the v2.2.0
 * release date 2021-11-10) against the v2.2.0 algorithms, plus the
 * self-contained regression cases mirrored from upstream tests/stemtest.c.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "libstemmer.h"

#define EMOJI_FACE_THROWING_A_KISS "\xf0\x9f\x98\x98"
#define U_40079 "\xf1\x80\x81\xb9"

static int failures = 0;
static int checks = 0;

static void expect_stem(const char *lang, const char *input, const char *want)
{
    struct sb_stemmer *st = sb_stemmer_new(lang, NULL);
    const sb_symbol *got;
    int len;

    checks++;
    if (st == NULL) {
        fprintf(stderr, "FAIL: stemmer '%s' unavailable\n", lang);
        failures++;
        return;
    }
    got = sb_stemmer_stem(st, (const unsigned char *)input, (int)strlen(input));
    if (got == NULL) {
        fprintf(stderr, "FAIL: %s: sb_stemmer_stem(%s) returned NULL\n", lang, input);
        failures++;
        sb_stemmer_delete(st);
        return;
    }
    len = sb_stemmer_length(st);
    if (len != (int)strlen(want) || memcmp(got, want, (size_t)len) != 0) {
        fprintf(stderr, "FAIL: %s: %s -> %.*s, want %s\n",
                lang, input, len, (const char *)got, want);
        failures++;
    } else {
        printf("ok %s: %s -> %.*s\n", lang, input, len, (const char *)got);
    }
    sb_stemmer_delete(st);
}

int main(void)
{
    const char **list;
    const char *need[] = {
        "arabic", "armenian", "english", "finnish", "german", "greek",
        "hindi", "hungarian", "nepali", "porter", "romanian", "russian",
        "serbian", "tamil", "turkish", "yiddish", NULL
    };
    int n = 0;
    const char **p;
    const char **q;
    struct sb_stemmer *koi8;

    /* 1) inventory: 29 canonical algorithms, key members present */
    list = sb_stemmer_list();
    if (list == NULL) {
        fprintf(stderr, "FAIL: sb_stemmer_list() returned NULL\n");
        return 1;
    }
    for (p = list; *p; ++p) n++;
    checks++;
    if (n < 29) {
        fprintf(stderr, "FAIL: only %d canonical algorithms (expected >= 29)\n", n);
        failures++;
    } else {
        printf("ok inventory: %d canonical algorithms\n", n);
    }
    for (q = need; *q; ++q) {
        int found = 0;
        checks++;
        for (p = list; *p; ++p) {
            if (strcmp(*p, *q) == 0) { found = 1; break; }
        }
        if (!found) {
            fprintf(stderr, "FAIL: algorithm '%s' missing from sb_stemmer_list()\n", *q);
            failures++;
        }
    }

    /* 2) alias resolution: ISO 639 code "en" -> english */
    expect_stem("en", "running", "run");

    /* 3) stem expectations across languages (pinned from the
     *    release-dated data run, UTF-8) */
    expect_stem("porter",     "running",       "run");
    expect_stem("english",    "consignments",  "consign");
    expect_stem("english",    "happiness",     "happi");
    expect_stem("spanish",    "caminando",     "camin");
    expect_stem("italian",    "ciclisti",      "ciclist");
    expect_stem("portuguese", "ciclistas",     "ciclist");
    expect_stem("dutch",      "gesten",        "gest");
    expect_stem("norwegian",  "husene",        "hus");
    expect_stem("danish",     "undrende",      "undr");
    expect_stem("swedish",    "uskickhet",     "uskick");
    expect_stem("german",     "aufeinander",   "aufeinand");
    expect_stem("french",     "continuera",    "continu");
    expect_stem("french",     "chevaux",       "cheval");
    expect_stem("russian",    "\xd0\xbf\xd0\xbe\xd1\x80\xd0\xbe\xd0\xb4\xd1\x8b",
                                "\xd0\xbf\xd0\xbe\xd1\x80\xd0\xbe\xd0\xb4");
    expect_stem("turkish",    "kitaplar\xc4\xb1", "kitap");
    expect_stem("arabic",     "\xd9\x83\xd8\xa7\xd8\xaa\xd8\xa8\xd9\x88\xd9\x86",
                                "\xd9\x83\xd8\xa7\xd8\xaa\xd8\xa8");
    expect_stem("tamil",      "\xe0\xae\xb5\xe0\xae\xbe\xe0\xae\xb0\xe0\xaf\x8d\xe0\xae\xa4\xe0\xaf\x8d\xe0\xae\xa4\xe0\xaf\x88\xe0\xae\x95\xe0\xae\xb3\xe0\xaf\x8d",
                                "\xe0\xae\xb5\xe0\xae\xbe\xe0\xae\xb0\xe0\xaf\x8d\xe0\xae\xa4\xe0\xaf\x8d\xe0\xae\xa4\xe0\xaf\x88");
    expect_stem("yiddish",    "\xd7\x91\xd7\x99\xd7\x9b\xd7\xa2\xd7\xa8",
                                "\xd7\x91\xd7\x99\xd7\x9b");

    /* 4) upstream stemtest regressions (mirrored):
     *    emoji mutation, private-use U+40079, numeric-damage #66/#81 */
    expect_stem("en", "a" EMOJI_FACE_THROWING_A_KISS "ing",
                     "a" EMOJI_FACE_THROWING_A_KISS "e");
    expect_stem("en", U_40079 "wing", U_40079 "wing");
    expect_stem("finnish", "2000", "2000");
    expect_stem("danish", "space1999", "space1999");

    /* 5) alternate encoding: russian in KOI8-R is registered */
    checks++;
    koi8 = sb_stemmer_new("russian", "KOI8_R");
    if (koi8 == NULL) {
        fprintf(stderr, "FAIL: russian/KOI8_R stemmer unavailable\n");
        failures++;
    } else {
        printf("ok encoding: russian KOI8_R available\n");
        sb_stemmer_delete(koi8);
    }

    printf("test_snowball: %d checks, %d failures\n", checks, failures);
    return failures == 0 ? 0 : 1;
}
