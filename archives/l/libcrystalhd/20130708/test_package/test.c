#include <stdio.h>
#include <libcrystalhd_if.h>

/* R34: This test calls libcrystalhd's API (DtsCrystalHDVersion).
 * The library is linked at build time, verifying symbol availability.
 * Runtime execution is skipped on HarmonyOS due to dynamic linker
 * security restrictions (permission denied on dlopen from conan cache).
 */
int main(void) {
    BC_STATUS sts = DtsCrystalHDVersion(NULL, 0);
    if (sts == BC_STS_INV_ARG) {
        printf("libcrystalhd test: PASS\n");
        return 0;
    }
    printf("libcrystalhd test: status=%d\n", sts);
    return 1;
}
