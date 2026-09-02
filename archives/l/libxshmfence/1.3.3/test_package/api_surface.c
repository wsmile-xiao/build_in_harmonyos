/*
 * libxshmfence 1.3.3 ABI surface test.
 *
 * Every exported function of libxshmfence.so.1 is forced into a live
 * relocation via a typed function pointer, so a missing implementation or a
 * signature mismatch fails at link/load time.  The check is display
 * independent and needs no X server.
 */

#include <stdio.h>
#include <X11/xshmfence.h>

#define DECLARE_SYMBOL(name) \
    static __typeof__(&name) volatile probe_##name = &name

/* struct xshmfence is opaque; every API takes a struct xshmfence * or an int. */
DECLARE_SYMBOL(xshmfence_trigger);
DECLARE_SYMBOL(xshmfence_await);
DECLARE_SYMBOL(xshmfence_query);
DECLARE_SYMBOL(xshmfence_reset);
DECLARE_SYMBOL(xshmfence_alloc_shm);
DECLARE_SYMBOL(xshmfence_map_shm);
DECLARE_SYMBOL(xshmfence_unmap_shm);

int main(void) {
    /* Force a live relocation against every exported symbol so that any
     * missing implementation in libxshmfence.so.1 fails at link or load
     * time, not silently at runtime. */
    (void)probe_xshmfence_trigger;
    (void)probe_xshmfence_await;
    (void)probe_xshmfence_query;
    (void)probe_xshmfence_reset;
    (void)probe_xshmfence_alloc_shm;
    (void)probe_xshmfence_map_shm;
    (void)probe_xshmfence_unmap_shm;
    printf("libxshmfence api surface: all 7 symbols resolved\n");
    return 0;
}
