#include <stdio.h>
#include <string.h>

#include "libinjection.h"
#include "libinjection_sqli.h"

int main(void) {
    struct libinjection_sqli_state state;
    const char *sqli = "1 or 1=1--";       /* classic SQL injection */
    const char *benign = "hello world";    /* benign input */
    int is_sqli, is_benign;
    int failures = 0;

    /* Payload that must be flagged as SQLi */
    libinjection_sqli_init(&state, sqli, strlen(sqli), 0);
    is_sqli = libinjection_is_sqli(&state);
    if (is_sqli != 1) {
        printf("FAIL: expected SQLi detection for '%s', got %d\n", sqli, is_sqli);
        failures++;
    } else {
        printf("OK: '%s' detected as SQLi (fingerprint=%s)\n",
               sqli, state.fingerprint);
    }

    /* Benign input must not be flagged */
    libinjection_sqli_init(&state, benign, strlen(benign), 0);
    is_benign = libinjection_is_sqli(&state);
    if (is_benign != 0) {
        printf("FAIL: expected benign for '%s', got %d\n", benign, is_benign);
        failures++;
    } else {
        printf("OK: '%s' not flagged\n", benign);
    }

    /* Version API returns a non-empty string */
    if (!libinjection_version() || strlen(libinjection_version()) == 0) {
        printf("FAIL: empty version string\n");
        failures++;
    } else {
        printf("OK: libinjection version %s\n", libinjection_version());
    }

    if (failures) {
        printf("test libinjection 3.9.2: %d FAILURE(S)\n", failures);
        return 1;
    }
    printf("test libinjection 3.9.2: OK\n");
    return 0;
}