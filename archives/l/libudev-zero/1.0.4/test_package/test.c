#include <libudev.h>
#include <stdio.h>

int main(void) {
    /* Test udev context creation and destruction */
    struct udev *udev = udev_new();
    if (udev == NULL) {
        fprintf(stderr, "FAIL: udev_new() returned NULL\n");
        return 1;
    }

    /* Test reference counting */
    struct udev *ref = udev_ref(udev);
    if (ref == NULL) {
        fprintf(stderr, "FAIL: udev_ref() returned NULL\n");
        udev_unref(udev);
        return 1;
    }

    udev_unref(ref);
    udev_unref(udev);

    printf("libudev-zero test: OK (udev_new/ref/unref)\n");
    return 0;
}
