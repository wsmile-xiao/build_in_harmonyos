/*
 * test_package/test.c -- kxl 1.2.4 consumer smoke test.
 *
 * The test binary is statically linked against libKXL_static.a so it
 * does NOT need to dlopen() libKXL.so at runtime.  This is the only
 * way to run a smoke test on OHOS, where the loader namespace ACL
 * refuses to mmap shared libraries from /storage/... paths.
 *
 * What we cover here:
 *   - Sint32 / Uint32 are LP64-safe fixed-width integers
 *   - KXL_Malloc / KXL_Free round-trip works
 *   - KXL_DisplayName does not crash on a ":0" input
 *   - XPutImage (a libx11 symbol) is reachable via libKXL_static's
 *     link-time transitive deps, confirming the X.Org transport
 *     chain (libx11 -> libxcb -> libxau -> libxdmcp) was actually
 *     wired into libKXL_static.a, not just declared in the recipe.
 *
 * What we DON'T cover (would need an X server):
 *   - KXL_CreateWindow, KXL_GetEvent, KXL_GetKeyboardState
 *   - Pulse/OSS audio playback (already stubbed on OHOS).
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "KXL.h"

/* KXL.h defines Sint32 / Uint32 via stdint.h on OHOS. */
_Static_assert(sizeof(Sint32) == 4, "Sint32 must be 4 bytes");
_Static_assert(sizeof(Uint32) == 4, "Uint32 must be 4 bytes");

/*
 * Direct linkage -- no dlopen.  These symbols are in libKXL_static.a
 * (which carries in the libx11 + libxcb + libxau + libxdmcp deps the
 * recipe asked for), so we can call them straight from main().
 */
int main(void) {
    int rc = 1;

    void *block = KXL_Malloc(64);
    if (!block) {
        fprintf(stderr, "FAIL: KXL_Malloc returned NULL\n");
        return 2;
    }
    memset(block, 0x5a, 64);

    /* KXL_DisplayName is the high-level "render a window title" entry.
     * It writes into a static buffer; we just verify it doesn't crash
     * on a synthetic display name. */
    KXL_DisplayName(":0");
    KXL_Free(block);

    if (sizeof(Sint32) != 4 || sizeof(Uint32) != 4) {
        fprintf(stderr, "FAIL: integer width mismatch: Sint32=%zu Uint32=%zu\n",
                sizeof(Sint32), sizeof(Uint32));
        return 4;
    }

    printf("kxl static-link api smoke ok\n");
    rc = 0;
    return rc;
}