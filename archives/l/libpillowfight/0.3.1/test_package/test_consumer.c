#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>
#define NO_PYTHON
#include <pillowfight/pillowfight.h>

int main(void) {
    const char *version = pf_get_version();

    printf("libpillowfight version: %s\n", version);
    assert(version != NULL && "pf_get_version() returned NULL");
    assert(strcmp(version, "0.3.1") == 0 && "pf_get_version() did not return expected version 0.3.1");

    printf("Consumer test PASSED: pf_get_version() returned '%s'\n", version);
    return 0;
}
