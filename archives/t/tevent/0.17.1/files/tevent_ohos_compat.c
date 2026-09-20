/*
 * tevent's bundled lib/replace maps memset_s() to rep_memset_s() when the
 * target libc does not provide the C11 Annex K interface (replace.h:
 * "#define memset_s rep_memset_s").  OHOS/musl has no memset_s, and tevent's
 * replace.c cannot be compiled on its own because it expects the full
 * autoconf feature matrix emitted by waf (AC_LIBREPLACE_NETWORK_CHECKS,
 * HAVE_FTRUNCATE, ...).  Rather than build all of replace.c we provide the
 * single symbol tevent actually references (tevent_signal.o and
 * tevent_epoll.o, reached through ZERO_STRUCT/BURN_DATA).
 *
 * Semantics mirror lib/replace/replace.c verbatim: EINVAL for a NULL
 * destination, ERANGE when destsz/count overflow RSIZE_MAX or count exceeds
 * destsz (still zeroing destsz bytes), otherwise 0.  Stores go through a
 * volatile pointer so the wipe cannot be optimised away, matching the
 * upstream HAVE_GCC_VOLATILE_MEMORY_PROTECTION branch.
 */
#include <errno.h>
#include <stddef.h>
#include <stdint.h>

int rep_memset_s(void *dest, size_t destsz, int ch, size_t count)
{
    volatile unsigned char *cursor;

    if (dest == NULL) {
        return EINVAL;
    }
    if (destsz > (SIZE_MAX >> 1) || count > (SIZE_MAX >> 1) || count > destsz) {
        cursor = (volatile unsigned char *)dest;
        while (destsz-- != 0) {
            *cursor++ = (unsigned char)ch;
        }
        return ERANGE;
    }

    cursor = (volatile unsigned char *)dest;
    while (count-- != 0) {
        *cursor++ = (unsigned char)ch;
    }
    return 0;
}
