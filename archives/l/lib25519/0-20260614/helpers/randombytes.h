// OHOS build-time randombytes() header — API-identical to upstream
// librandombytes (librandombytes-20240318/include/randombytes.h,
// public domain, djb). Do NOT change the signature: upstream
// command/lib25519-test.c does `#include <randombytes.h>` and then
// `#define knownrandombytes randombytes` + `void knownrandombytes(void
// *xvoid,long long xlen)`, which after macro expansion must match this
// declaration exactly, or clang reports "conflicting types for
// 'randombytes'".
//
// public API: randombytes()

#ifndef randombytes_h
#define randombytes_h

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

#endif
