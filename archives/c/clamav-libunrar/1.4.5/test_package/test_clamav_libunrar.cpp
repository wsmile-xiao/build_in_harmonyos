// Consumer test for clamav-libunrar: exercises the public UnRAR C API
// (dll.hpp) against the packaged clamunrar library. All four checks call
// real library entry points; a stub or mis-linked library fails them.
#include <cstdio>
#include <cstring>

#include "raros.hpp" // defines _UNIX on OHOS/Linux, required by dll.hpp
#include "dll.hpp"

static int g_checks = 0;
static int g_passed = 0;

static void check(bool ok, const char *name) {
    ++g_checks;
    if (ok) {
        ++g_passed;
        std::printf("PASS: %s\n", name);
    } else {
        std::printf("FAIL: %s\n", name);
    }
}

int main() {
    // 1. Library version matches the RAR_DLL_VERSION ABI constant (8).
    check(RARGetDllVersion() == RAR_DLL_VERSION, "RARGetDllVersion == RAR_DLL_VERSION");

    // 2. Opening a missing archive reports ERAR_EOPEN via the Ex API.
    struct RAROpenArchiveDataEx openEx;
    std::memset(&openEx, 0, sizeof(openEx));
    char arcName[] = "hmbs_definitely_missing_9f3k2.rar";
    openEx.ArcName = arcName;
    openEx.OpenMode = RAR_OM_LIST;
    HANDLE hArc = RAROpenArchiveEx(&openEx);
    check(openEx.OpenResult == ERAR_EOPEN, "RAROpenArchiveEx missing archive -> ERAR_EOPEN");

    // 3. The failed-open handle closes cleanly (NULL handle is also valid).
    bool closeOk = (hArc == NULL) || (RARCloseArchive(hArc) == ERAR_SUCCESS);
    check(closeOk, "RARCloseArchive after failed open");

    // 4. The ANSI variant reports ERAR_EOPEN as well.
    struct RAROpenArchiveData openData;
    std::memset(&openData, 0, sizeof(openData));
    openData.ArcName = arcName;
    openData.OpenMode = RAR_OM_LIST;
    HANDLE hArc2 = RAROpenArchive(&openData);
    bool ansiOk = (openData.OpenResult == ERAR_EOPEN);
    if (hArc2 != NULL) {
        RARCloseArchive(hArc2);
    }
    check(ansiOk, "RAROpenArchive missing archive -> ERAR_EOPEN");

    std::printf("clamav-libunrar checks: %d/%d passed\n", g_passed, g_checks);
    return (g_passed == g_checks) ? 0 : 1;
}
