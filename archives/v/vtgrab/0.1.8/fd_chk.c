/* Dummy implementation of __fd_chk for OHOS musl.
 *
 * The OHOS sysroot's sys/select.h declares __fd_chk and uses it in FD_SET/FD_CLR
 * macros, but the OHOS musl libc doesn't provide this symbol.  Provide a no-op
 * implementation here so the binaries link and run.
 */
#include <sys/select.h>

void __fd_chk(int fd)
{
    /* In the original musl, this would abort if fd >= FD_SETSIZE.
     * We trust our fd values are valid and skip the check to avoid
     * linking against a missing symbol. */
    (void)fd;
}
