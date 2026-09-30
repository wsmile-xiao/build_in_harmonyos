#include <errno.h>
#include <stdio.h>

#include <dfu/libdfu.h>

int main(void)
{
    int progress = -1;
    int finished = -1;
    int result = dfu_flash_filename(
        "/this/path/does/not/exist/libdfu-test-firmware.bin",
        &progress,
        &finished);

    if (result != ENODEV) {
        fprintf(stderr, "expected ENODEV (%d), got %d\n", ENODEV, result);
        return 1;
    }

    puts("libdfu consumer error-path test passed");
    return 0;
}
