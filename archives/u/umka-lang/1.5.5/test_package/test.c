#include <stdio.h>
#include <string.h>
#include "umka_api.h"

int main(void) {
    /* Verify umkaGetVersion returns a non-empty string */
    const char *version = umkaGetVersion();
    if (!version || strlen(version) == 0) {
        printf("FAIL: umkaGetVersion returned empty\n");
        return 1;
    }
    printf("umka version: %s\n", version);

    /* Allocate and initialize an Umka interpreter with a simple script */
    Umka *umka = umkaAlloc();
    if (!umka) {
        printf("FAIL: umkaAlloc returned NULL\n");
        return 1;
    }

    bool ok = umkaInit(umka, "test.um",
        "fn main() { printf(\"Hello from Umka!\\n\") }",
        1024 * 1024, NULL, 0, NULL, false, false, NULL);

    if (ok) {
        ok = umkaCompile(umka);
    }

    if (!ok) {
        UmkaError *err = umkaGetError(umka);
        printf("FAIL: umka compile error: %s\n", err ? err->msg : "unknown");
        umkaFree(umka);
        return 1;
    }

    int result = umkaRun(umka);
    printf("umka run result: %d\n", result);

    umkaFree(umka);

    if (result != 0) {
        printf("FAIL: umkaRun returned %d\n", result);
        return 1;
    }

    printf("umka-lang test: OK\n");
    return 0;
}
