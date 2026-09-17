/* Consumer-side randombytes() for test_package (static-link helper).
 *
 * Same implementation as ../../helpers/randombytes.c (kept as a separate
 * copy so test_package is self-contained): OHOS getrandom(2) with a
 * /dev/urandom fallback. API-identical to upstream librandombytes
 * (`void randombytes(void *,long long)` via the
 * randombytes_internal_void_voidstar_longlong macro); the header is
 * included so this definition provides the exact symbol the static
 * lib25519 archive references. Fail-closed: aborts instead of returning
 * predictable bytes when no entropy source is available.
 */

#include <errno.h>
#include <fcntl.h>
#include <stddef.h>
#include <stdlib.h>
#include <unistd.h>
#include <sys/random.h>

#include "randombytes_ohos.h"

void randombytes(void *xvoid, long long xlen)
{
    unsigned char *x = (unsigned char *)xvoid;
    unsigned long long want;
    unsigned long long done = 0;

    if (xlen <= 0)
        return;
    want = (unsigned long long)xlen;

    while (done < want) {
        ssize_t r = getrandom(x + done, (size_t)(want - done), 0);
        if (r < 0) {
            if (errno == EINTR)
                continue;
            break;
        }
        done += (unsigned long long)r;
    }

    if (done < want) {
        int fd = open("/dev/urandom", O_RDONLY);
        if (fd < 0)
            abort();
        while (done < want) {
            ssize_t r = read(fd, x + done, (size_t)(want - done));
            if (r < 0) {
                if (errno == EINTR)
                    continue;
                close(fd);
                abort();
            }
            if (r == 0) {
                close(fd);
                abort();
            }
            done += (unsigned long long)r;
        }
        close(fd);
    }
}

const char *randombytes_source(void)
{
    return "ohos-getrandom-devurandom";
}
