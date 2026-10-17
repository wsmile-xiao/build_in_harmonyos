/* Shared header of the lib32-gcc consumer flow (test_package/).
 *
 * The marker below is expanded by the *preprocessor* stage of the packaged
 * cross-compiler: the recipe injects gcc/config/ohos.h into the ARM Linux
 * EABI tm_file list, so __OHOS__ is visible before any code is generated.
 * consumer_probe.c turns this macro into a printable literal that the test
 * asserts on in the -E output, and consumer_lib.c binds it into the linked
 * program so the OHOS target identity survives all the way to the artifact.
 */

#ifndef LIB32_GCC_CONSUMER_LIB_H
#define LIB32_GCC_CONSUMER_LIB_H

#ifdef __OHOS__
#define CONSUMER_TARGET_ABI_MARKER "arm-linux-ohos-32bit-abi"
#else
#define CONSUMER_TARGET_ABI_MARKER "unexpected-non-ohos-abi"
#endif

/* Defined in consumer_lib.c (translation unit A). */
int consumer_compute(int n);
int consumer_checksum(const char *text);
const char *consumer_target_abi(void);

#endif /* LIB32_GCC_CONSUMER_LIB_H */
