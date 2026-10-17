/*
 * OHOS-specific consumer test — libvpl 2.16.0 on HarmonyOS PC.
 *
 * Guards the two facts this adaptation depends on:
 *
 * 1. The shipped libvpl.so contains the *complete* dispatcher, i.e. the
 *    legacy 1.x entry points (MFXInit / MFXInitEx / MFXQueryVersion /
 *    MFXClose) that upstream compiles only under `if(UNIX)` in
 *    libvpl/CMakeLists.txt.  A plain native configure on this platform leaves
 *    UNIX undefined (uname -s = "HarmonyOS"), which silently drops
 *    libvpl/src/linux/mfxloader.cpp and leaves a libvpl.so exporting just the
 *    seven 2.x loader symbols.  Referencing these functions makes the L1 test
 *    fail to link if that regression returns; the status assertions below then
 *    prove the legacy dispatcher actually runs.
 *
 * 2. No Intel runtime is reachable on OHOS, so the dispatcher must report the
 *    documented "not found" statuses instead of failing or crashing.
 *
 * Expected return codes were measured on the packaged build:
 *   MFXInit/MFXInitEx        -> MFX_ERR_UNSUPPORTED  (no MSDK runtime found)
 *   MFXQueryVersion(NULL)    -> MFX_ERR_INVALID_HANDLE
 *   MFXClose(NULL)           -> MFX_ERR_INVALID_HANDLE
 *   unfiltered enumeration   -> MFX_ERR_NOT_FOUND, out-parameter untouched
 *   MFXCreateSession         -> MFX_ERR_NOT_FOUND, session stays NULL
 *
 * 9 checks.
 */
#include <stdio.h>

#include <vpl/mfxdispatcher.h>
#include <vpl/mfxvideo.h>

static int g_checks;
static int g_failed;

static void check(int cond, const char *what) {
    g_checks++;
    if (cond) {
        printf("ok   - %s\n", what);
    } else {
        g_failed++;
        printf("FAIL - %s\n", what);
    }
}

int main(void) {
    mfxStatus sts;

    /* 1. header/package version consistency */
    check(MFX_VERSION_MAJOR == 2 && MFX_VERSION_MINOR == 16,
          "vpl/mfxdefs.h declares MFX_VERSION 2.16 (matches package version)");

    /* 2-3. legacy 1.x dispatcher is present and reaches its search logic */
    mfxVersion ver = {0};
    mfxSession session = NULL;
    sts = MFXInit(MFX_IMPL_AUTO_ANY, &ver, &session);
    check(sts == MFX_ERR_UNSUPPORTED,
          "MFXInit(MFX_IMPL_AUTO_ANY) == MFX_ERR_UNSUPPORTED (no MSDK runtime on OHOS)");
    check(session == NULL, "MFXInit() leaves the session NULL when it fails");

    mfxInitParam par = {0};
    par.Implementation = MFX_IMPL_AUTO_ANY;
    par.Version        = ver;
    sts = MFXInitEx(par, &session);
    check(sts == MFX_ERR_UNSUPPORTED,
          "MFXInitEx() == MFX_ERR_UNSUPPORTED (no MSDK runtime on OHOS)");

    /* 4-5. legacy session entry points validate their handle argument */
    check(MFXQueryVersion(NULL, &ver) == MFX_ERR_INVALID_HANDLE,
          "MFXQueryVersion(NULL, &ver) == MFX_ERR_INVALID_HANDLE");
    check(MFXClose(NULL) == MFX_ERR_INVALID_HANDLE,
          "MFXClose(NULL) == MFX_ERR_INVALID_HANDLE");

    /* 6-7. no implementation is reachable, and the loader says so cleanly */
    mfxLoader loader = MFXLoad();
    check(loader != NULL, "MFXLoad() returns a loader handle");
    if (loader == NULL) {
        printf("test_libvpl_ohos: FAILED (%d/%d checks)\n",
               g_checks - g_failed, g_checks);
        return 1;
    }

    mfxHDL idesc = (mfxHDL)0x1; /* poison: must stay untouched on failure */
    sts = MFXEnumImplementations(loader, 0, MFX_IMPLCAPS_IMPLDESCSTRUCTURE, &idesc);
    check(sts == MFX_ERR_NOT_FOUND && idesc == (mfxHDL)0x1,
          "unfiltered MFXEnumImplementations() == MFX_ERR_NOT_FOUND without an Intel runtime");

    session = NULL;
    sts = MFXCreateSession(loader, 0, &session);
    check(sts == MFX_ERR_NOT_FOUND && session == NULL,
          "MFXCreateSession() == MFX_ERR_NOT_FOUND without an Intel runtime");
    MFXUnload(loader);

    printf("test_libvpl_ohos: %s (%d/%d checks)\n",
           g_failed == 0 ? "OK" : "FAILED", g_checks - g_failed, g_checks);
    return g_failed == 0 ? 0 : 1;
}
