#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

#include <drm.h>
#include <drm_fourcc.h>
#include <xf86drm.h>

/* Consumer smoke test: exercise real libdrm API surface.
 * The CI host has no DRM device, so the API contract is verified
 * through documented error paths (non-DRM fd must fail cleanly). */

static int failures = 0;

#define CHECK(cond, msg)                        \
    do {                                        \
        if (cond) {                             \
            printf("PASS: %s\n", msg);          \
        } else {                                \
            printf("FAIL: %s\n", msg);          \
            failures++;                         \
        }                                       \
    } while (0)

int main(void) {
    /* Link-time check: the wrapped library exports the xf86drm API. */
    CHECK(drmGetVersion != NULL && drmFreeVersion != NULL &&
              drmGetCap != NULL,
          "xf86drm symbols resolved");

    int fd = open("/dev/null", O_RDWR | O_CLOEXEC);
    CHECK(fd >= 0, "open /dev/null as non-DRM fd");

    /* drmGetVersion on a non-DRM fd must fail with NULL, not crash. */
    errno = 0;
    drmVersionPtr v = drmGetVersion(fd);
    CHECK(v == NULL, "drmGetVersion(non-DRM fd) returns NULL");
    CHECK(errno == ENOTTY, "errno is ENOTTY for non-DRM fd");

    /* drmFreeVersion(NULL) is documented to be a no-op. */
    drmFreeVersion(NULL);
    drmFreeVersion(v);
    CHECK(1, "drmFreeVersion handles NULL safely");

    /* drmGetCap on a non-DRM fd must report failure. */
    uint64_t value = 0xdeadbeef;
    int rc = drmGetCap(fd, DRM_CAP_PRIME, &value);
    CHECK(rc != 0, "drmGetCap(non-DRM fd) reports failure");

    close(fd);

    if (failures) {
        printf("test libdrm 2.4.133: %d failure(s)\n", failures);
        return 1;
    }
    printf("test libdrm 2.4.133: OK\n");
    return 0;
}
