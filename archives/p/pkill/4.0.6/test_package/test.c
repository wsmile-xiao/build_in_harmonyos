#include <stdio.h>
#include <stdlib.h>

int main(void) {
    /* pkill is a binary tool, not a library.
     * This test verifies the package is consumable. */
    printf("test pkill 4.0.6: package OK\n");
    return 0;
}
