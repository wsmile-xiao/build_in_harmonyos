/* Translation unit B of the lib32-gcc consumer flow (test_package/).
 *
 * This file only sees the declarations in consumer_lib.h, so it is compiled
 * with consumer_compute/consumer_checksum/consumer_target_abi as UNDEFINED
 * symbols.  The link step (stage 6) is what proves the packaged assembler and
 * the device GNU ld really resolved the cross-translation-unit references.
 */

#include "consumer_lib.h"

int main(void) {
    if (consumer_compute(100) != 5050) {
        return 1;
    }
    if (consumer_checksum("arm-linux-ohos") == 0) {
        return 2;
    }
    if (consumer_target_abi()[0] != 'a') {
        return 3;
    }
    return 0;
}
