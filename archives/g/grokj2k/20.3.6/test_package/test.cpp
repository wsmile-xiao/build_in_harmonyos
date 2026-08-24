/* test_grokj2k — verify grokj2k library links and API is callable */
#include <cstdio>
#include <cstring>
#include <cstdlib>

#include "grok.h"

int main(void)
{
    /* 1. Verify grk_version() returns a non-empty string */
    const char* ver = grk_version();
    if (!ver || ver[0] == '\0') {
        fprintf(stderr, "FAIL: grk_version() returned NULL or empty\n");
        return 1;
    }
    printf("grokj2k version: %s\n", ver);

    /* 2. Verify version string starts with expected major.minor */
    if (strncmp(ver, "20.3", 4) != 0) {
        fprintf(stderr, "FAIL: expected version starting with '20.3', got '%s'\n", ver);
        return 1;
    }

    printf("PASS: grokj2k library linked and API functional\n");
    return 0;
}
