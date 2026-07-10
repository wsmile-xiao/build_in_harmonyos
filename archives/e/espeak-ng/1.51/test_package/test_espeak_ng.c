#include <espeak-ng/espeak_ng.h>
#include <espeak-ng/speak_lib.h>
#include <stdio.h>
#include <string.h>

int main() {
    const char *version = espeak_Info(NULL);
    if (version && strlen(version) > 0) {
        printf("espeak-ng version: %s\n", version);
        printf("Test PASSED\n");
        return 0;
    } else {
        printf("Test FAILED: no version string\n");
        return 1;
    }
}
