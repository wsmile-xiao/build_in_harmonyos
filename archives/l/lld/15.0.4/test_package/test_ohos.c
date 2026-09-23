#include <stdio.h>
#include <stdint.h>

/* HarmonyOS AArch64-specific consumer test for the packaged lld linker.
 * Built with -fuse-ld=<packaged ld.lld> so the whole link step runs
 * through the delivered linker on the OHOS aarch64 target.  Also prints
 * a UINTPTR_MAX-derived value so the executable proves the AArch64
 * data model at runtime. */
int main(void) {
    uintptr_t word_size = (uintptr_t)-1 > UINT32_MAX ? 64 : 32;
    if (printf("harmonyos-lld-consumer word_size=%u\n",
               (unsigned)word_size) <= 0) {
        return 1;
    }
    return word_size == 64 ? 0 : 2;
}
