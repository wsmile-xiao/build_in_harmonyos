/*
 * libxshmfence 1.3.3 version contract.
 *
 * Two layers, both display independent:
 *   1. Compile-time signature contracts: assigning &name to a typed function
 *      pointer fails to compile under -Werror if the upstream header ever
 *      changes a signature.
 *   2. A real functional smoke test: allocate, map, trigger, query, reset and
 *      await a fence.  The primary allocation path is memfd_create(2) with a
 *      SHMDIR-backed mkostemp fallback, so this needs no X server.
 */

#include <stdio.h>
#include <X11/xshmfence.h>

#define CHECK(cond, msg)                                                     \
    do {                                                                     \
        if (!(cond)) {                                                       \
            fprintf(stderr, "FAIL: %s\n", msg);                              \
            return 1;                                                        \
        }                                                                    \
        printf("ok: %s\n", msg);                                             \
    } while (0)

/* ---- compile-time signature contracts (must stay in sync with xshmfence.h) */
static int (*const sig_xshmfence_trigger)(struct xshmfence *) =
    xshmfence_trigger;
static int (*const sig_xshmfence_await)(struct xshmfence *) =
    xshmfence_await;
static int (*const sig_xshmfence_query)(struct xshmfence *) =
    xshmfence_query;
static void (*const sig_xshmfence_reset)(struct xshmfence *) =
    xshmfence_reset;
static int (*const sig_xshmfence_alloc_shm)(void) =
    xshmfence_alloc_shm;
static struct xshmfence *(*const sig_xshmfence_map_shm)(int) =
    xshmfence_map_shm;
static void (*const sig_xshmfence_unmap_shm)(struct xshmfence *) =
    xshmfence_unmap_shm;

int main(void) {
    (void)sig_xshmfence_trigger;
    (void)sig_xshmfence_await;
    (void)sig_xshmfence_query;
    (void)sig_xshmfence_reset;
    (void)sig_xshmfence_alloc_shm;
    (void)sig_xshmfence_map_shm;
    (void)sig_xshmfence_unmap_shm;
    printf("ok: 7 xshmfence signature contracts\n");

    /* ---- functional smoke test on a real fence ---- */
    int fd = xshmfence_alloc_shm();
    CHECK(fd >= 0, "xshmfence_alloc_shm returns valid fd");

    struct xshmfence *fence = xshmfence_map_shm(fd);
    CHECK(fence != NULL, "xshmfence_map_shm maps fence");

    CHECK(xshmfence_query(fence) == 0, "fence is initially untriggered");
    CHECK(xshmfence_trigger(fence) == 0, "xshmfence_trigger succeeds");
    CHECK(xshmfence_query(fence) == 1, "fence is triggered after trigger");

    xshmfence_reset(fence);
    CHECK(xshmfence_query(fence) == 0, "fence is reset after reset");

    CHECK(xshmfence_trigger(fence) == 0, "xshmfence_trigger succeeds again");
    CHECK(xshmfence_await(fence) == 0, "xshmfence_await returns when triggered");

    xshmfence_unmap_shm(fence);
    printf("libxshmfence version contract: all checks passed\n");
    return 0;
}
