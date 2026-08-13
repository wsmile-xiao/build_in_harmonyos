#include <stdio.h>
#include <hidapi/hidapi.h>

int main(void) {
    if (hid_init() != 0) {
        fprintf(stderr, "hid_init failed\n");
        return 1;
    }

    /* 枚举所有 HID 设备（无物理设备时返回 NULL，属正常） */
    struct hid_device_info *devs = hid_enumerate(0, 0);
    hid_free_enumeration(devs);

    if (hid_exit() != 0) {
        fprintf(stderr, "hid_exit failed\n");
        return 2;
    }

    printf("test hidapi 0.12: OK\n");
    return 0;
}
