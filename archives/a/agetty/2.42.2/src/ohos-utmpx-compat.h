/*
 * OHOS musl libc utmpx.h only defines struct utmpx; it does NOT declare the
 * GNU utmpx API (utmpxname/setutxent/getutxent/pututxline/endutxent/updwtmpx)
 * and libc.so exports no vhangup symbol. agetty(8) from util-linux 2.42.2
 * calls these, so we forward-declare them for the OHOS build.
 */
#ifndef OHOS_UTMPX_COMPAT_H
#define OHOS_UTMPX_COMPAT_H

#include <utmpx.h>
#include <sys/types.h>

#ifdef __cplusplus
extern "C" {
#endif

void utmpxname(const char *file);
void setutxent(void);
struct utmpx *getutxent(void);
struct utmpx *pututxline(const struct utmpx *ut);
void endutxent(void);
void updwtmpx(const char *file, const struct utmpx *ut);
int vhangup(void);

#ifdef __cplusplus
}
#endif

#endif /* OHOS_UTMPX_COMPAT_H */
