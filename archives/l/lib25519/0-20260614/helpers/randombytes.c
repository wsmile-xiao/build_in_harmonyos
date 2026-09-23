/* Minimal randombytes() implementation for HarmonyOS (musl).
 *
 * API-identical to upstream librandombytes
 * (librandombytes-20240318/kernel/randombytes.c, public domain, djb):
 * the header declares `extern void randombytes(void *,long long)` via the
 * `randombytes_internal_void_voidstar_longlong` macro, and this file
 * includes the header so the definition below provides that exact symbol.
 * The (void *,long long) shape is mandatory: upstream
 * command/lib25519-test.c includes <randombytes.h> and then redefines the
 * symbol deterministically as `void knownrandombytes(void *xvoid,long long
 * xlen)` with `#define knownrandombytes randombytes`; any other prototype
 * (e.g. an unsigned-char pointer with unsigned-long-long length) breaks the test compile with
 * "conflicting types for 'randombytes'".
 *
 * Why this file exists: upstream lib25519 links its shared library and its
 * test/benchmark tools against librandombytes
 * (https://randombytes.cr.yp.to, same djb family as libcpucycles), which has
 * not been adapted to this registry yet. The static archive itself only
 * carries an *undefined* reference to randombytes() (called by the
 * crypto_dh/crypto_sign keypair wrappers); the symbol must be resolved at
 * final link time. Rather than blocking lib25519 on a second adaptation,
 * the recipe stages this small helper (OHOS getrandom(2) with a
 * /dev/urandom fallback) purely as a *build-time* link input:
 *
 *   - the shared lib25519.so.1 links the static helper archive, so no
 *     DT_NEEDED on an external librandombytes is created;
 *   - static-archive consumers (e.g. test_package) compile this same file
 *     alongside their test source (see test_package/randombytes_ohos.c).
 *
 * Once librandombytes is published in the registry, this helper should be
 * replaced by a real `self.requires("librandombytes/...")`.
 *
 * Fail-closed: if neither getrandom(2) nor /dev/urandom can deliver bytes,
 * the process aborts instead of returning predictable data.
 */

#include <errno.h>
#include <fcntl.h>
#include <stddef.h>
#include <stdlib.h>
#include <unistd.h>
#include <sys/random.h>

#include "randombytes.h"

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
