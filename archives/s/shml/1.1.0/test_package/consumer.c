/* OHOS aarch64 consumer of shml.
 * shml_output.h is generated at build time by sourcing the *packaged* shml.sh with bash
 * and calling fgcolor/bgcolor/attribute/hr/icon. This program parses that stream like a
 * terminal front end: it strips SGR escape sequences, then checks the SGR parameters and
 * the remaining text against oracles that are independent of shml (ECMA-48 codes). */
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#include "shml_output.h"

static const int expected_sgr[] = {31, 39, 44, 49, 1, 0};
static const char expected_plain[] = "OHOS PC qemu B **** \xE2\x9C\x93";

int main(void) {
    char plain[256];
    size_t plain_len = 0;
    int sgr[16];
    int nsgr = 0;
    size_t i = 0;

    while (i < shml_output_len) {
        if (shml_output[i] == 0x1B && i + 1 < shml_output_len && shml_output[i + 1] == '[') {
            int param = 0;
            i += 2;
            while (i < shml_output_len && shml_output[i] >= '0' && shml_output[i] <= '9')
                param = param * 10 + (shml_output[i++] - '0');
            if (i >= shml_output_len || shml_output[i] != 'm' || nsgr >= 16) {
                fputs("FAIL: malformed or excess SGR sequence in shml output\n", stderr);
                return 1;
            }
            sgr[nsgr++] = param;
            i++;
        } else {
            if (plain_len + 1 >= sizeof(plain)) {
                fputs("FAIL: shml output too long\n", stderr);
                return 2;
            }
            plain[plain_len++] = (char)shml_output[i++];
        }
    }
    plain[plain_len] = '\0';

    if (nsgr != (int)(sizeof(expected_sgr) / sizeof(expected_sgr[0])) ||
        memcmp(sgr, expected_sgr, sizeof(expected_sgr)) != 0) {
        fprintf(stderr, "FAIL: unexpected SGR sequence list (%d codes)\n", nsgr);
        return 3;
    }
    if (strcmp(plain, expected_plain) != 0) {
        fprintf(stderr, "FAIL: unexpected plain text: %s\n", plain);
        return 4;
    }
    printf("shml OHOS consumer PASS: %d SGR codes, plain text \"%s\"\n", nsgr, plain);
    return 0;
}
