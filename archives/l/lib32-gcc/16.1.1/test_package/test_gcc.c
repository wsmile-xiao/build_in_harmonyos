/* HarmonyOS consumer feasibility test for the lib32-gcc (arm-linux-ohos)
   32-bit ARM cross-compiler.

   Compiled by the packaged driver, this must produce a 32-bit ARM ELF that
   targets arm-linux-ohos.  The test_package validates the ELF instead of
   executing it, because an ARM binary cannot run on the aarch64 host.

   When EXPECT_OHOS=1 (set on OHOS) the program also asserts that the
   cross-compiler defines __OHOS__ and that the target ABI is 32-bit, which
   proves the OHOS target adaptation is wired correctly end to end. */

#ifndef EXPECT_OHOS
#define EXPECT_OHOS 0
#endif

int compute(int n) {
    int s = 0;
    for (int i = 0; i < n; ++i) {
        s += i;
    }
    return s;
}

int main(void) {
#if EXPECT_OHOS
    #ifndef __OHOS__
    #error "lib32-gcc did not define __OHOS__ for the arm-linux-ohos target"
    #endif
    /* arm-linux-ohos is a 32-bit target: pointers and ints are 4 bytes. */
    _Static_assert(sizeof(void *) == 4, "arm-linux-ohos target must be 32-bit");
    _Static_assert(sizeof(int) == 4, "int must be 32-bit on arm-linux-ohos");
#endif
    return compute(100) == 4950 ? 0 : 1;
}
