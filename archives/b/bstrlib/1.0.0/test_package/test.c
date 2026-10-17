#include <stdio.h>
#include <string.h>
#include "bstrlib.h"

/* R34: test_package must actually exercise the package API. */
int main(void) {
    bstring b = bfromcstr("Hello, bstrlib!");
    if (!b) {
        printf("bstrlib consumer test: FAILED (bfromcstr returned NULL)\n");
        return 1;
    }
    int rv = biseqcstr(b, "Hello, bstrlib!");
    printf("bstrlib consumer test: %s\n", rv == 1 ? "PASS" : "FAIL");
    bdestroy(b);
    return rv == 1 ? 0 : 1;
}
