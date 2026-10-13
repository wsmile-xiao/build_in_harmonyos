// Layer-2 consumer validation for rocm-core/7.2.4.
//
// This program links the packaged rocm-core library and calls its real
// exported C API (rocm_version.h / rocm_getpath.h), asserting the returned
// values against the compile-time ROCM_VERSION_* macros and the ROCM_PATH
// override behaviour. It returns non-zero if any check fails so that the
// conan test() step fails the build.

#include <rocm_version.h>
#include <rocm_getpath.h>

#include <cstdio>
#include <cstdlib>
#include <cstring>

static unsigned long g_checks = 0;
static unsigned long g_failed = 0;

static void check(bool cond, const char* what) {
    ++g_checks;
    if (!cond) {
        ++g_failed;
        std::fprintf(stderr, "FAIL: %s\n", what);
    } else {
        std::printf("ok: %s\n", what);
    }
}

int main() {
    // --- 1. getROCmVersion() returns the packaged ROCM_VERSION_* macros ----
    unsigned int major = 0, minor = 0, patch = 0;
    VerErrors rc = getROCmVersion(&major, &minor, &patch);
    check(rc == VerSuccess, "getROCmVersion() returns VerSuccess");
    check(major == ROCM_VERSION_MAJOR, "major == ROCM_VERSION_MAJOR");
    check(minor == ROCM_VERSION_MINOR, "minor == ROCM_VERSION_MINOR");
    check(patch == ROCM_VERSION_PATCH, "patch == ROCM_VERSION_PATCH");
    check(major == 7u && minor == 2u && patch == 4u,
          "reported version is exactly 7.2.4");
    std::printf("rocm-core version: %u.%u.%u (macros %d.%d.%d)\n",
                major, minor, patch,
                ROCM_VERSION_MAJOR, ROCM_VERSION_MINOR, ROCM_VERSION_PATCH);

    // --- 2. ROCM_BUILD_INFO macro + printBuildInfo() ----------------------
    check(std::strncmp(ROCM_BUILD_INFO, "7.2.4", 5) == 0,
          "ROCM_BUILD_INFO starts with 7.2.4");
    check(printBuildInfo() == VerSuccess,
          "printBuildInfo() returns VerSuccess");

    // --- 3. getROCmInstallPath() honours the ROCM_PATH override -----------
    // The returned length is the string length of the install path including
    // its trailing '/' (rocm_getpath.cpp returns strlen(ROCM_PATH) + 1).
    if (setenv("ROCM_PATH", "/opt/rocm", 1) != 0) {
        std::perror("setenv");
        return 2;
    }
    char* path = NULL;
    unsigned int len = 0;
    PathErrors_t prc = getROCmInstallPath(&path, &len);
    check(prc == PathSuccess,
          "getROCmInstallPath(ROCM_PATH=/opt/rocm) returns PathSuccess");
    check(path != NULL, "install path pointer is non-null");
    if (path != NULL) {
        check(std::strcmp(path, "/opt/rocm/") == 0,
              "install path == /opt/rocm/");
        check(len == (unsigned int)std::strlen(path),
              "returned length == strlen(path)");
        check(len == 10u, "returned length == 10 for /opt/rocm/");
        std::printf("rocm install path: %s (len=%u)\n", path, len);
        std::free(path);
    }

    // --- 4. ROCM_PATH is re-read on each call (no stale static buffer) ----
    if (setenv("ROCM_PATH", "/usr/lib/rocm", 1) != 0) {
        std::perror("setenv");
        return 2;
    }
    char* path2 = NULL;
    unsigned int len2 = 0;
    PathErrors_t prc2 = getROCmInstallPath(&path2, &len2);
    check(prc2 == PathSuccess,
          "getROCmInstallPath(ROCM_PATH=/usr/lib/rocm) returns PathSuccess");
    if (path2 != NULL) {
        check(std::strcmp(path2, "/usr/lib/rocm/") == 0,
              "second call reflects the updated ROCM_PATH");
        std::printf("rocm install path (2nd): %s (len=%u)\n", path2, len2);
        std::free(path2);
    }

    // --- 5. getROCmVersion(): NULL out-parameters ------------------------
    // The upstream public headers declare this function
    // ATTRIBUTE_NON_NULL = __attribute__((nonnull)), so from -O1 upwards clang
    // is entitled to assume the out-parameters are never NULL and folds away the
    // upstream `NULL_CHECK` guards. Compiled that way (the initial Release -O3
    // build) these three calls did not return an error code at all -- they
    // SIGSEGV'd (exit 139). conanfile.py therefore builds the library with
    // -fno-delete-null-pointer-checks so the guards survive as written.
    // DO NOT remove that flag: without it this section crashes the test binary.
    // (The literal NULL arguments below are intentional and produce harmless
    // -Wnonnull warnings -- that warning is exactly the trap being guarded here.)
    unsigned int n1 = 0, n2 = 0, n3 = 0;
    check(getROCmVersion(NULL, &n2, &n3) == VerIncorrectParameters,
          "getROCmVersion(NULL Major) returns VerIncorrectParameters");
    check(getROCmVersion(&n1, NULL, &n3) == VerIncorrectParameters,
          "getROCmVersion(NULL Minor) returns VerIncorrectParameters");
    check(getROCmVersion(&n1, &n2, NULL) == VerIncorrectParameters,
          "getROCmVersion(NULL Patch) returns VerIncorrectParameters");

    // --- 6. getROCmInstallPath(): NULL arguments -------------------------
    // NULL_CHECK order in rocm_getpath.cpp is InstallPath first, then
    // InstallPathLen; both return PathIncorrecPararmeters (-994).
    char* nullprobe = NULL;
    unsigned int nlen = 0;
    check(getROCmInstallPath(NULL, &nlen) == PathIncorrecPararmeters,
          "getROCmInstallPath(NULL InstallPath) returns PathIncorrecPararmeters");
    check(getROCmInstallPath(&nullprobe, NULL) == PathIncorrecPararmeters,
          "getROCmInstallPath(NULL InstallPathLen) returns PathIncorrecPararmeters");
    check(getROCmInstallPath(NULL, NULL) == PathIncorrecPararmeters,
          "getROCmInstallPath(NULL,NULL) returns PathIncorrecPararmeters");

    // --- 7. getROCmInstallPath(): ROCM_PATH unset / empty ----------------
    // Static build (BUILD_SHARED_LIBS=0): with no ROCM_PATH there is no runtime
    // library to dlopen for the base path, so upstream returns
    // PathLinuxRuntimeErrors (-998). An empty ROCM_PATH takes the same path
    // (getenv is non-NULL but len == 0). Sentinels prove the function resets
    // both out-parameters on failure (no dangling pointer, no stale length).
    if (unsetenv("ROCM_PATH") != 0) {
        std::perror("unsetenv");
        return 2;
    }
    char* upath = (char*)0xdeadbeef;
    unsigned int ulen = 0x12345u;
    PathErrors_t urc = getROCmInstallPath(&upath, &ulen);
    check(urc == PathLinuxRuntimeErrors,
          "getROCmInstallPath(ROCM_PATH unset, static) returns PathLinuxRuntimeErrors");
    check(upath == NULL, "on failure *InstallPath is reset to NULL");
    check(ulen == 0u, "on failure *InstallPathLen is reset to 0");

    if (setenv("ROCM_PATH", "", 1) != 0) {
        std::perror("setenv");
        return 2;
    }
    char* epath = (char*)0xdeadbeef;
    unsigned int elen = 0x12345u;
    check(getROCmInstallPath(&epath, &elen) == PathLinuxRuntimeErrors,
          "getROCmInstallPath(ROCM_PATH empty) returns PathLinuxRuntimeErrors");
    check(epath == NULL, "empty ROCM_PATH: *InstallPath is reset to NULL");

    // --- 8. getROCmInstallPath(): ROCM_PATH longer than PATH_MAX ---------
    // rocm_getpath.cpp rejects len > RC_PATH_MAX-1, where RC_PATH_MAX is
    // PATH_MAX+1 (PATH_MAX == 4096 on this platform) -> PathValuesTooLong (-996).
    static char oversized[8192];
    std::memset(oversized, 'a', sizeof(oversized) - 1);
    oversized[0] = '/';
    oversized[sizeof(oversized) - 1] = '\0';
    if (setenv("ROCM_PATH", oversized, 1) != 0) {
        std::perror("setenv");
        return 2;
    }
    char* bpath = (char*)0xdeadbeef;
    unsigned int blen = 0x12345u;
    PathErrors_t brc = getROCmInstallPath(&bpath, &blen);
    check(brc == PathValuesTooLong,
          "getROCmInstallPath(ROCM_PATH > PATH_MAX) returns PathValuesTooLong");
    check(bpath == NULL, "over-long ROCM_PATH: *InstallPath is reset to NULL");
    check(blen == 0u, "over-long ROCM_PATH: *InstallPathLen is reset to 0");

    // --- 9. trailing-slash quirk (documented upstream behaviour) ---------
    // rocm_getpath.cpp appends '/' unless it sees one at envStr[len]; len is the
    // strlen, so that test reads the terminating NUL and never matches. The
    // intended strip is therefore dead code and a trailing slash is doubled.
    // Asserted here so the behaviour is pinned and a future change is noticed.
    if (setenv("ROCM_PATH", "/opt/rocm/", 1) != 0) {
        std::perror("setenv");
        return 2;
    }
    char* tpath = NULL;
    unsigned int tlen = 0;
    PathErrors_t trc = getROCmInstallPath(&tpath, &tlen);
    check(trc == PathSuccess, "ROCM_PATH with trailing slash returns PathSuccess");
    if (tpath != NULL) {
        check(std::strcmp(tpath, "/opt/rocm//") == 0,
              "trailing slash is doubled (documented upstream quirk)");
        check(tlen == 11u, "trailing-slash length is 11");
        std::printf("trailing-slash result: %s (len=%u)\n", tpath, tlen);
        std::free(tpath);
    }

    std::printf("rocm-core consumer checks: %lu executed, %lu failed\n",
                g_checks, g_failed);
    return g_failed == 0 ? 0 : 1;
}
