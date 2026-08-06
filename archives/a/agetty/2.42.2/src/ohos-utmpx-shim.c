/*
 * OHOS musl libc does not export GNU utmpx functions
 * (utmpxname/setutxent/getutxent/pututxline/endutxent/updwtmpx).
 * agetty(8) from util-linux requires them (configure hard gate gnu_utmpx).
 * These no-op implementations let the build link on OHOS.
 */
#include <utmpx.h>
#include <stddef.h>
#include <sys/syscall.h>
#include <unistd.h>

void utmpxname(const char *file) { (void)file; }
void setutxent(void) {}
struct utmpx *getutxent(void) { return NULL; }
struct utmpx *pututxline(const struct utmpx *ut) { (void)ut; return NULL; }
void endutxent(void) {}
void updwtmpx(const char *file, const struct utmpx *ut) { (void)file; (void)ut; }

/* vhangup(2): OHOS libc does not export it; syscall exists (__NR_vhangup 58). */
int vhangup(void)
{
	return (int)syscall(SYS_vhangup);
}
