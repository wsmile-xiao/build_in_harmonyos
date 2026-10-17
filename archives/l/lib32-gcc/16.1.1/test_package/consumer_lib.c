/* Translation unit A of the lib32-gcc consumer flow (test_package/).
 *
 * Compiled on its own to a 32-bit ARM relocatable object by the packaged
 * cross-compiler; the link step later resolves these symbols from the second
 * translation unit.  A broken or stubbed package cannot produce an object
 * that the device GNU ld accepts together with consumer_main.o.
 */

#include "consumer_lib.h"

int consumer_compute(int n) {
    int sum = 0;
    int i = 0;
    for (i = 1; i <= n; ++i) {
        sum += i;
    }
    return sum;
}

int consumer_checksum(const char *text) {
    int mixed = 0;
    while (*text != '\0') {
        mixed = (mixed * 33) ^ (unsigned char)*text;
        ++text;
    }
    return mixed;
}

const char *consumer_target_abi(void) {
    return CONSUMER_TARGET_ABI_MARKER;
}
