#include <errno.h>
#include <stddef.h>
#include <stdint.h>

/*
 * talloc's bundled replace layer maps memset_s to rep_memset_s when the
 * target libc does not provide Annex K.  Keep the implementation local and
 * use volatile stores so clearing cannot be optimized away.
 */
int rep_memset_s(void *dest, size_t destsz, int ch, size_t count)
{
    volatile unsigned char *cursor;

    if (dest == NULL || destsz > (SIZE_MAX >> 1)) {
        return EINVAL;
    }
    if (count > destsz) {
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
