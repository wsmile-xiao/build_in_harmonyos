#include <stdio.h>
#include <labjackusb.h>

int main(void) {
    float version = LJUSB_GetLibraryVersion();
    printf("exodriver (liblabjackusb) library version: %.4f\n", version);
    if (version < 2.0f) {
        fprintf(stderr, "ERROR: unexpected library version %.4f\n", version);
        return 1;
    }
    printf("exodriver smoke test: OK\n");
    return 0;
}
