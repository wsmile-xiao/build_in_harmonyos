#include <stdio.h>
#include <stdlib.h>
#include "tesseract/capi.h"

int main(void) {
    const char *version = TessVersion();
    if (version) {
        printf("tesseract version: %s\n", version);
        printf("test tesseract 5.5.3: OK\n");
        return 0;
    } else {
        printf("test tesseract 5.5.3: FAIL (no version)\n");
        return 1;
    }
}
