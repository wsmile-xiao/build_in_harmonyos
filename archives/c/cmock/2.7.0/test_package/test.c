#include <stdio.h>

#include "cmock.h"

int main(void)
{
    CMOCK_MEM_INDEX_TYPE index;

    CMock_Guts_MemFreeAll();
    if (CMock_Guts_MemBytesUsed() != 0) {
        return 1;
    }

    index = CMock_Guts_MemNew(32);
    if (index == CMOCK_GUTS_NONE) {
        return 2;
    }
    if (CMock_Guts_GetAddressFor(index) == NULL) {
        return 3;
    }
    if (CMock_Guts_MemBytesUsed() == 0) {
        return 4;
    }

    CMock_Guts_MemFreeAll();
    if (CMock_Guts_MemBytesUsed() != 0) {
        return 5;
    }

    puts("cmock consumer OK: runtime allocation and reset verified");
    return 0;
}
