/*
 * HarmonyOS-specific consumer case: integer arithmetic across two calls.
 *
 * Compiled by the packaged amd64-linux-pcc on HarmonyOS PC, then assembled and
 * linked into a real x86-64 ELF executable by the on-device toolchain.  The
 * case deliberately avoids system headers: the package ships no amd64 libc.
 */
int pcc_add(int a, int b) { return a + b; }

int pcc_mul(int a, int b) { return a * b; }

int entry(void) { return pcc_add(pcc_mul(6, 7), 0); }
