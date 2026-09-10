#include <stdio.h>
#include <libevdev/libevdev.h>
#include <linux/input.h>

int main(void) {
    /* Test libevdev_event_type_get_name - does not require a device */
    const char *type_name = libevdev_event_type_get_name(EV_KEY);
    if (type_name == NULL) {
        fprintf(stderr, "FAIL: libevdev_event_type_get_name(EV_KEY) returned NULL\n");
        return 1;
    }
    printf("EV_KEY -> %s\n", type_name);

    /* Test libevdev_event_code_get_name */
    const char *code_name = libevdev_event_code_get_name(EV_KEY, BTN_LEFT);
    if (code_name == NULL) {
        fprintf(stderr, "FAIL: libevdev_event_code_get_name(EV_KEY, BTN_LEFT) returned NULL\n");
        return 1;
    }
    printf("BTN_LEFT -> %s\n", code_name);

    /* Test libevdev_new / libevdev_free lifecycle */
    struct libevdev *dev = libevdev_new();
    if (dev == NULL) {
        fprintf(stderr, "FAIL: libevdev_new() returned NULL\n");
        return 1;
    }
    libevdev_free(dev);

    printf("libevdev test: OK\n");
    return 0;
}
