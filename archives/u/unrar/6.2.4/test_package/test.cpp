#define _UNIX
#include <stdio.h>
#include <string.h>
#include "dll.hpp"

int main() {
    int version = RARGetDllVersion();
    if (version != RAR_DLL_VERSION) {
        printf("FAIL: RARGetDllVersion() returned %d, expected %d\n", version, RAR_DLL_VERSION);
        return 1;
    }
    printf("OK: RARGetDllVersion() = %d\n", version);

    struct RAROpenArchiveDataEx open_data;
    memset(&open_data, 0, sizeof(open_data));
    open_data.ArcName = (char*)"nonexistent_archive.rar";
    open_data.OpenMode = RAR_OM_EXTRACT;
    HANDLE h = RAROpenArchiveEx(&open_data);
    if (h != NULL) {
        RARCloseArchive(h);
        printf("FAIL: RAROpenArchiveEx should return NULL\n");
        return 1;
    }
    if (open_data.OpenResult == ERAR_SUCCESS) {
        printf("FAIL: OpenResult should be error\n");
        return 1;
    }
    printf("OK: RAROpenArchiveEx correctly failed (error=%d)\n", open_data.OpenResult);
    return 0;
}
