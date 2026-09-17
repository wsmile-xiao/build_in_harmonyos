/* randombytes.c — minimal build-time shim of the librandombytes API.
 *
 * Public domain (CC0-1.0). See randombytes.h for rationale and migration path.
 *
 * Behavior matches the upstream contract: randombytes() always succeeds from
 * the caller's perspective. Bytes come from /dev/urandom (present on OHOS);
 * reads handle EINTR internally; any hard failure aborts loudly instead of
 * returning weak bytes, so a broken entropy source can never silently pass
 * the lib1305 test suite.
 */

#include <unistd.h>
#include <fcntl.h>
#include <errno.h>
#include <stdlib.h>

#include "randombytes.h"

static int rb_fd = -1;

__attribute__((constructor))
static void rb_init(void)
{
  /* Opened once at startup and kept for process lifetime, mirroring the
   * upstream note that randombytes may keep a file descriptor open. */
  rb_fd = open("/dev/urandom", O_RDONLY);
}

void randombytes(void *xvoid,long long xlen)
{
  unsigned char *x = (unsigned char *)xvoid;

  if (rb_fd < 0)
    abort();

  while (xlen > 0) {
    ssize_t r = read(rb_fd, x, (size_t)xlen);
    if (r < 0) {
      if (errno == EINTR)
        continue;
      abort();
    }
    if (r == 0)
      abort();
    x += r;
    xlen -= r;
  }
}
