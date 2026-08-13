#include <sane/sane.h>

#include <stdio.h>

int main(void) {
    SANE_Int version_code = 0;
    const SANE_Device **devices = NULL;
    SANE_Status status = sane_init(&version_code, NULL);

    if (status != SANE_STATUS_GOOD) {
        fprintf(stderr, "sane_init failed: %s\n", sane_strstatus(status));
        return 1;
    }

    status = sane_get_devices(&devices, SANE_FALSE);
    if (status != SANE_STATUS_GOOD) {
        fprintf(stderr, "sane_get_devices failed: %s\n", sane_strstatus(status));
        sane_exit();
        return 1;
    }

    if (!devices || !devices[0]) {
        fprintf(stderr, "test backend did not expose a device\n");
        sane_exit();
        return 1;
    }

    SANE_Handle handle = NULL;
    status = sane_open(devices[0]->name, &handle);
    if (status != SANE_STATUS_GOOD) {
        fprintf(stderr, "sane_open failed: %s\n", sane_strstatus(status));
        sane_exit();
        return 1;
    }

    sane_close(handle);
    printf("SANE test backend opened, version=%d, device=%s\n", version_code, devices[0]->name);
    sane_exit();
    return 0;
}
