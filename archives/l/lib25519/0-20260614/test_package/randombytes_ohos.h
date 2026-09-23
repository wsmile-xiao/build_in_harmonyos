#ifndef RANDOMBYTES_OHOS_H
#define RANDOMBYTES_OHOS_H

/* Consumer-side randombytes() declaration for test_package.
 *
 * API-identical to upstream librandombytes
 * (librandombytes-20240318/include/randombytes.h, public domain, djb):
 * `extern void randombytes(void *,long long)` via the
 * `randombytes_internal_void_voidstar_longlong` macro. The recipe's
 * build-time helper (helpers/randombytes.{h,c}) provides that exact
 * symbol, and the static lib25519 archive references it, so this header
 * must declare the same prototype or the final link leaves an undefined
 * reference.
 *
 * The static lib25519 archive references randombytes() (keypair wrappers)
 * without defining it; static consumers must resolve it at final link.
 * This test links randombytes_ohos.c (OHOS getrandom(2) + /dev/urandom
 * fallback, fail-closed) alongside the test source. Shared-library
 * consumers need nothing extra: lib25519.so.1 already embeds the helper.
 */

#define randombytes randombytes_internal_void_voidstar_longlong
#define randombytes_source randombytes_internal_source

#ifdef __cplusplus
extern "C" {
#endif

extern void randombytes(void *,long long) __attribute__((visibility("default")));
extern const char *randombytes_source(void) __attribute__((visibility("default")));

#ifdef __cplusplus
}
#endif

#endif /* RANDOMBYTES_OHOS_H */
