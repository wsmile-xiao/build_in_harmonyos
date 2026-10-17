// Consumer test for libclamunrar: exercises the real UnRAR DLL API
// (dll.hpp) without requiring a RAR compressor to craft archives.
// Three deterministic cases:
//  1) RARGetDllVersion() must equal RAR_DLL_VERSION (8).
//  2) RAROpenArchive() on a missing file must report ERAR_EOPEN (15).
//  3) RAROpenArchiveEx() on a missing file must report ERAR_EOPEN (15).
// Any deviation exits non-zero so the harness genuinely fails.
#include <cstdio>
#include <cstring>

#include "dll.hpp"

static int failures = 0;

#define CHECK(cond, fmt, ...)                                          \
    do {                                                               \
        if (cond) {                                                    \
            std::printf("PASS: " fmt "\n", ##__VA_ARGS__);              \
        } else {                                                       \
            std::printf("FAIL: " fmt "\n", ##__VA_ARGS__);              \
            ++failures;                                                \
        }                                                              \
    } while (0)

int main() {
    // Case 1: DLL version matches the header contract.
    int version = RARGetDllVersion();
    CHECK(version == RAR_DLL_VERSION, "RARGetDllVersion()=%d expected %d",
          version, RAR_DLL_VERSION);

    // Case 2: opening a missing archive reports EOPEN and returns null.
    // Single CHECK: OpenResult contract + null handle + leak-free close.
    struct RAROpenArchiveData openData;
    std::memset(&openData, 0, sizeof(openData));
    char missing[] = "hmbs-missing-archive-1.4.4.rar";
    openData.ArcName = missing;
    openData.OpenMode = RAR_OM_LIST;
    openData.OpenResult = ERAR_SUCCESS;
    HANDLE handle = RAROpenArchive(&openData);
    bool openOk = (openData.OpenResult == ERAR_EOPEN && handle == nullptr);
    if (handle != nullptr) {
        RARCloseArchive(handle);  // never expected; avoid leaking on surprise
    }
    CHECK(openOk, "RAROpenArchive(missing): OpenResult=%u handle=%p (expect %u/null)",
          openData.OpenResult, handle, (unsigned)ERAR_EOPEN);

    // Case 3: Ex variant behaves the same on a missing file (single CHECK).
    struct RAROpenArchiveDataEx openEx;
    std::memset(&openEx, 0, sizeof(openEx));
    openEx.ArcName = missing;
    openEx.OpenMode = RAR_OM_LIST;
    openEx.OpenResult = ERAR_SUCCESS;
    HANDLE handleEx = RAROpenArchiveEx(&openEx);
    bool openExOk = (openEx.OpenResult == ERAR_EOPEN && handleEx == nullptr);
    if (handleEx != nullptr) {
        RARCloseArchive(handleEx);
    }
    CHECK(openExOk, "RAROpenArchiveEx(missing): OpenResult=%u handle=%p (expect %u/null)",
          openEx.OpenResult, handleEx, (unsigned)ERAR_EOPEN);

    if (failures == 0) {
        std::printf("ALL 3 CONSUMER CHECKS PASSED\n");
        return 0;
    }
    std::printf("%d CHECK(S) FAILED\n", failures);
    return 1;
}
