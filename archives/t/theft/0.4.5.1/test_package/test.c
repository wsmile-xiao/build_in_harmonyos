#include <stdint.h>
#include <stdlib.h>

#include <theft.h>

int main(void) {
    static const uint8_t input[] = "harmonyos-theft";
    theft_hash value = theft_hash_onepass(input, sizeof(input) - 1);
    return value == 0 ? EXIT_FAILURE : EXIT_SUCCESS;
}
