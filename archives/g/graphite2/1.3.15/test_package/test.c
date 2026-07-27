#include <stdio.h>
#include <stdlib.h>
#include "graphite2/Font.h"

int main(void) {
    /* Test that graphite2 API is accessible at link time */
    int nMajor = 0, nMinor = 0, nBugFix = 0;
    gr_engine_version(&nMajor, &nMinor, &nBugFix);
    printf("graphite2 engine version: %d.%d.%d\n", nMajor, nMinor, nBugFix);

    if (nMajor > 0 || (nMajor == 0 && nMinor > 0)) {
        printf("test_graphite2: PASSED (v%d.%d.%d)\n", nMajor, nMinor, nBugFix);
        return 0;
    } else {
        fprintf(stderr, "test_graphite2: FAILED (v%d.%d.%d)\n", nMajor, nMinor, nBugFix);
        return 1;
    }
}