/*
 * Consumer test — libvpl 2.16.0 (Intel oneVPL dispatcher) on HarmonyOS PC.
 *
 * Drives the public 2.x loader API exactly as an application would
 * (MFXLoad -> MFXCreateConfig -> MFXSetConfigFilterProperty ->
 * MFXEnumImplementations -> MFXCreateSession -> MFXUnload) and asserts the
 * documented status/out-parameter contract.  The assertions hold on any
 * machine: when no runtime implementation is reachable the dispatcher must
 * report MFX_ERR_NOT_FOUND instead of crashing or returning garbage.
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

    /* 1. loader handle */
    mfxLoader loader = MFXLoad();
    check(loader != NULL, "MFXLoad() returns a loader handle");
    if (loader == NULL) {
        printf("test_libvpl: FAILED (%d/%d checks)\n", g_checks - g_failed, g_checks);
        return 1;
    }

    /* 2. configuration object */
    mfxConfig cfg = MFXCreateConfig(loader);
    check(cfg != NULL, "MFXCreateConfig() returns a config handle");
    if (cfg == NULL) {
        /* 不继续用 NULL 句柄调用后续 API：避免级联失败掩盖首个根因 */
        printf("test_libvpl: FAILED (%d/%d checks)\n", g_checks - g_failed, g_checks);
        MFXUnload(loader);
        return 1;
    }

    /* 3. property filter is accepted */
    mfxVariant impl;
    impl.Type    = MFX_VARIANT_TYPE_U32;
    impl.Data.U32 = MFX_IMPL_TYPE_HARDWARE;
    sts = MFXSetConfigFilterProperty(cfg, (const mfxU8 *)"mfxImplDescription.Impl", impl);
    check(sts == MFX_ERR_NONE,
          "MFXSetConfigFilterProperty(mfxImplDescription.Impl) == MFX_ERR_NONE");

    /* 4-5. enumeration returns a defined status and honours the out-parameter */
    mfxHDL idesc = NULL;
    sts = MFXEnumImplementations(loader, 0, MFX_IMPLCAPS_IMPLDESCSTRUCTURE, &idesc);
    check(sts == MFX_ERR_NONE || sts == MFX_ERR_NOT_FOUND,
          "MFXEnumImplementations() == MFX_ERR_NONE or MFX_ERR_NOT_FOUND");
    check((sts == MFX_ERR_NONE) == (idesc != NULL),
          "MFXEnumImplementations() sets the out-parameter iff MFX_ERR_NONE");
    if (idesc != NULL) {
        MFXDispReleaseImplDescription(loader, idesc);
    }

    /* 6-7. session creation returns a defined status and a consistent handle */
    mfxSession session = NULL;
    sts = MFXCreateSession(loader, 0, &session);
    check(sts == MFX_ERR_NONE || sts == MFX_ERR_NOT_FOUND,
          "MFXCreateSession() == MFX_ERR_NONE or MFX_ERR_NOT_FOUND");
    check((sts == MFX_ERR_NONE) == (session != NULL),
          "MFXCreateSession() sets the session iff MFX_ERR_NONE");
    if (session != NULL) {
        mfxVersion ver = {0};
        if (MFXQueryVersion(session, &ver) == MFX_ERR_NONE) {
            printf("info - dispatched runtime API version %d.%d\n", ver.Major, ver.Minor);
        }
        MFXClose(session);
    }

    /* 8. NULL out-parameter is rejected (documented API contract) */
    sts = MFXCreateSession(loader, 0, NULL);
    check(sts == MFX_ERR_NULL_PTR,
          "MFXCreateSession(loader, 0, NULL) == MFX_ERR_NULL_PTR");

    /* 9. unload / re-load round trip */
    MFXUnload(loader);
    mfxLoader again = MFXLoad();
    check(again != NULL, "MFXLoad() succeeds after MFXUnload()");
    if (again != NULL) {
        MFXUnload(again);
    }

    printf("test_libvpl: %s (%d/%d checks)\n",
           g_failed == 0 ? "OK" : "FAILED", g_checks - g_failed, g_checks);
    return g_failed == 0 ? 0 : 1;
}
