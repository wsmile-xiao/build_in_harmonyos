#include <stdio.h>
/* Include breakpad header to verify include paths are correct */
#include "google_breakpad/common/minidump_format.h"

int main(void) {
    /* Verify breakpad headers are accessible and package is linked */
    printf("test breakpad v2023.06.01: OK\n");
    return 0;
}
