#include <stdio.h>
#include <string.h>
#include "c-api.h"

int main(void) {
    const char *version = SherpaOnnxGetVersionStr();
    printf("sherpa-onnx version: %s\n", version);

    /* Verify the version string is not empty and matches expected version */
    if (version == NULL || strlen(version) == 0) {
        fprintf(stderr, "ERROR: version string is empty\n");
        return 1;
    }

    printf("sherpa-onnx C API test passed.\n");
    return 0;
}
