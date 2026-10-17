/*
 * Consumer-side verification for readstat/1.1.9 (HarmonyOS PC adaptation).
 *
 * Links ONLY against the packaged library through the installed public header
 * <readstat.h>, and exercises real library entry points:
 *
 *   1. parser object lifecycle (readstat_parser_init / _free)
 *   2. readstat_parse_sav() and readstat_parse_dta() on a missing file —
 *      must fail with READSTAT_ERROR_OPEN, never return READSTAT_OK
 *      ("empty input passes" would be the classic false-green here)
 *   3. readstat_error_message() mapping for OK / OPEN / PARSE
 *
 * Exit code 0 = all checks passed, 1 = at least one check failed.
 */
#include <stdio.h>
#include <string.h>

#include <readstat.h>

static int failures = 0;

static void check(int condition, const char *what) {
    if (condition) {
        printf("ok   : %s\n", what);
    } else {
        printf("FAIL : %s\n", what);
        failures++;
    }
}

int main(void) {
    readstat_parser_t *parser = readstat_parser_init();
    check(parser != NULL, "readstat_parser_init() returns a parser");

    if (parser == NULL) {
        return 1;
    }

    readstat_error_t err = readstat_parse_sav(parser, "no-such-file-readstat-1.1.9.sav", NULL);
    check(err == READSTAT_ERROR_OPEN,
          "readstat_parse_sav() on a missing file -> READSTAT_ERROR_OPEN");

    const char *msg = readstat_error_message(err);
    check(msg != NULL && strcmp(msg, "Unable to open file") == 0,
          "readstat_error_message(READSTAT_ERROR_OPEN) == \"Unable to open file\"");

    err = readstat_parse_dta(parser, "no-such-file-readstat-1.1.9.dta", NULL);
    check(err == READSTAT_ERROR_OPEN,
          "readstat_parse_dta() on a missing file -> READSTAT_ERROR_OPEN");

    err = readstat_parse_sas7bdat(parser, "no-such-file-readstat-1.1.9.sas7bdat", NULL);
    check(err == READSTAT_ERROR_OPEN,
          "readstat_parse_sas7bdat() on a missing file -> READSTAT_ERROR_OPEN");

    check(readstat_error_message(READSTAT_OK) == NULL,
          "readstat_error_message(READSTAT_OK) == NULL (documented behaviour)");
    check(readstat_error_message(READSTAT_ERROR_PARSE) != NULL,
          "readstat_error_message(READSTAT_ERROR_PARSE) is non-empty");

    readstat_parser_free(parser);

    printf("readstat 1.1.9 consumer check: %s (%d failure(s))\n",
           failures == 0 ? "PASS" : "FAIL", failures);
    return failures == 0 ? 0 : 1;
}
