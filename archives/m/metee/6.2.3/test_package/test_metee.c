#include <metee.h>
#include <stdio.h>
#include <string.h>

int main(void)
{
    TEEHANDLE handle;
    GUID guid;
    TEESTATUS status;

    memset(&handle, 0, sizeof(handle));
    memset(&guid, 0, sizeof(guid));

    status = TeeInit(&handle, &guid, NULL);
    printf("METEE_TEEINIT_STATUS=0x%04x\n", (unsigned)status);

    if (status == TEE_DEVICE_NOT_FOUND) {
        printf("METEE_OK_NO_DEVICE\n");
        return 0;
    }
    if (TEE_IS_SUCCESS(status)) {
        printf("METEE_OK_DEVICE\n");
        return 0;
    }
    return 1;
}
