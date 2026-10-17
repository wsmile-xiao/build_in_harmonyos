/* ohos_libc_compat.h — compatibility shim for HarmonyOS PC (musl-based libc).

   The OHOS libc (musl-derived) does not provide the POSIX-2008 locale-aware
   conversion functions (strtoll_l, strtoull_l, strtol_l, strtoul_l, strtod_l,
   strtof_l, strtold_l) that libc++ >= 17 uses in <locale>. musl ignores the
   locale argument, so mapping them to the plain (non-_l) versions is
   behaviourally equivalent for the C locale that libc++ requests.
*/
#ifndef OHOS_LIBC_COMPAT_H
#define OHOS_LIBC_COMPAT_H

#include <stdlib.h>

#ifdef __cplusplus
extern "C" {
#endif

static inline long long strtoll_l(const char* nptr, char** endptr, int base, void* loc) {
  (void)loc;
  return strtoll(nptr, endptr, base);
}
static inline unsigned long long strtoull_l(const char* nptr, char** endptr, int base, void* loc) {
  (void)loc;
  return strtoull(nptr, endptr, base);
}
static inline long strtol_l(const char* nptr, char** endptr, int base, void* loc) {
  (void)loc;
  return strtol(nptr, endptr, base);
}
static inline unsigned long strtoul_l(const char* nptr, char** endptr, int base, void* loc) {
  (void)loc;
  return strtoul(nptr, endptr, base);
}
static inline double strtod_l(const char* nptr, char** endptr, void* loc) {
  (void)loc;
  return strtod(nptr, endptr);
}
static inline float strtof_l(const char* nptr, char** endptr, void* loc) {
  (void)loc;
  return strtof(nptr, endptr);
}
static inline long double strtold_l(const char* nptr, char** endptr, void* loc) {
  (void)loc;
  return strtold(nptr, endptr);
}

#ifdef __cplusplus
}
#endif

#endif /* OHOS_LIBC_COMPAT_H */
