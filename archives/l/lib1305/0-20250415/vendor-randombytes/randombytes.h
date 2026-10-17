/* randombytes.h — minimal build-time shim of the librandombytes API.
 *
 * Public domain (CC0-1.0). Recipe-local build glue for lib1305 on OHOS:
 * librandombytes has no HarmonyOS adaptation in this repository yet, while
 * lib1305's shared-library link and its lib1305-test/lib1305-speed tools
 * unconditionally use `-lrandombytes`. The lib1305 library itself never
 * calls randombytes (verified: no reference in crypto_onetimeauth/,
 * crypto_verify/, dispatch/, cpuid/ or cryptoint/ sources), so this shim
 * only feeds the test/benchmark tools and the shared link line.
 *
 * API contract (per https://randombytes.cr.yp.to/api.html):
 *   #include <randombytes.h>
 *   randombytes(x, xbytes);   -- fills x[0..xbytes-1], always succeeds
 * Link with -lrandombytes.
 *
 * Migration path: replace this shim with
 *   self.requires("librandombytes/<ver>")
 * once librandombytes is adapted and published; then delete this directory
 * and drop the -I/-L injection in conanfile.py.
 */
#ifndef randombytes_h
#define randombytes_h

extern void randombytes(void *,long long);

#endif
