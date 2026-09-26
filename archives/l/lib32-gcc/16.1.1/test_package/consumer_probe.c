/* Preprocess-only probe of the lib32-gcc consumer flow (test_package/).
 *
 * The packaged driver must expose __OHOS__ to the preprocessor stage (the
 * recipe injects gcc/config/ohos.h after arm/linux-eabi.h).  Running
 * `gcc -E consumer_probe.c` therefore has to leave the arm-linux-ohos marker
 * literal in the output; the test asserts exactly that.
 */

#include "consumer_lib.h"

const char *consumer_probe(void) {
    return CONSUMER_TARGET_ABI_MARKER;
}
