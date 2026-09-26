// Consumer test for irstlm 6.00.05
// Verifies a third-party consumer can include public headers, link against
// libirstlm, and exercise a real public API (dictionary word <-> code roundtrip).
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "dictionary.h"

int main(void) {
    // Build an in-memory dictionary through the public constructor.
    dictionary dict((char *)"/dev/null");

    // Public API: enable incremental inserts so new words get distinct codes.
    dict.incflag(1);

    // Public API: encode() assigns a code, decode() returns the word back.
    const char *w1 = "hello";
    const char *w2 = "world";
    int c1 = dict.encode(w1);
    int c2 = dict.encode(w2);

    if (c1 < 0 || c2 < 0) {
        fprintf(stderr, "FAIL: encode returned invalid codes (%d, %d)\n", c1, c2);
        return 1;
    }
    if (c1 == c2) {
        fprintf(stderr, "FAIL: distinct words got the same code %d\n", c1);
        return 1;
    }

    const char *d1 = dict.decode(c1);
    const char *d2 = dict.decode(c2);
    if (!d1 || !d2 || strcmp(d1, w1) != 0 || strcmp(d2, w2) != 0) {
        fprintf(stderr, "FAIL: decode mismatch (%s, %s) vs (%s, %s)\n",
                d1 ? d1 : "(null)", d2 ? d2 : "(null)", w1, w2);
        return 1;
    }

    // Public API: size() must reflect the two inserted words (plus OOV symbol).
    if (dict.size() < 2) {
        fprintf(stderr, "FAIL: dictionary size %d < 2 after inserts\n", dict.size());
        return 1;
    }

    printf("consumer test passed: '%s'<->code %d, '%s'<->code %d, size %d\n",
           d1, c1, d2, c2, dict.size());
    return 0;
}
