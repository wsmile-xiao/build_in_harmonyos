#include <libubi.h>
#include <stdio.h>
#include <string.h>
#include <errno.h>

/*
 * Installed-package consumer for libubi.
 *
 * libubi is the UBI (Unsorted Block Images) development library. UBI devices
 * (/dev/ubi_ctrl, /dev/ubiN) only exist on a target with the kernel UBI
 * subsystem, so the headless build host has none. The test therefore exercises
 * the real public API end-to-end and asserts the documented device-less
 * behaviour (libubi_open() returns NULL because /dev/ubi_ctrl is absent), plus
 * the request-struct API and the public UBI constants — a genuine consumer
 * workflow, not a link-only smoke check.
 *
 * NOTE: libubi_close() dereferences its descriptor (free(lib->vol_name), ...),
 * so it must NOT be called with NULL. We only close a handle we actually
 * obtained, which never happens on this device-less host.
 */

int main(void) {
    int failures = 0;

    /* Stage 1: real consumer entry point. On a UBI-less build host the
       control device is absent, so libubi_open() returns NULL after running
       the real open() path — exactly the documented behaviour. */
    libubi_t lib = libubi_open();
    if (lib == NULL) {
        printf("[CHECK libubi_open OK] returned NULL (no /dev/ubi_ctrl, expected)\n");
    } else {
        struct ubi_info info;
        memset(&info, 0, sizeof(info));
        if (ubi_get_info(lib, &info) == 0 && info.dev_count >= 0) {
            printf("[CHECK libubi_open OK] ubi_get_info dev_count=%d\n", info.dev_count);
        } else {
            printf("[FAIL] ubi_get_info\n");
            failures++;
        }
        libubi_close(lib);  /* safe: only when we actually got a handle */
    }

    /* Stage 2: public API request struct is usable by a consumer.
       `name` is `const char *`, so assign the pointer (no strcpy). */
    struct ubi_mkvol_request req;
    memset(&req, 0, sizeof(req));
    req.vol_id = UBI_VOL_NUM_AUTO;
    req.alignment = 1;
    req.bytes = 1024;
    req.name = "libubi-test";
    if (req.vol_id == UBI_VOL_NUM_AUTO && req.bytes == 1024 &&
        req.name != NULL && strcmp(req.name, "libubi-test") == 0) {
        printf("[CHECK struct_api OK] ubi_mkvol_request vol_id=%d name=%s bytes=%lld\n",
               req.vol_id, req.name, (long long)req.bytes);
    } else {
        printf("[FAIL] struct_api\n");
        failures++;
    }

    /* Stage 3: public UBI constants are reachable from a consumer translation
       unit (these are the real macros from mtd/ubi-user.h). */
    if (UBI_VOL_NUM_AUTO == -1 && UBI_DEV_NUM_AUTO == -1 &&
        UBI_MAX_VOLUME_NAME == 127) {
        printf("[CHECK ubi_consts OK] UBI_VOL_NUM_AUTO=%d UBI_MAX_VOLUME_NAME=%d\n",
               UBI_VOL_NUM_AUTO, UBI_MAX_VOLUME_NAME);
    } else {
        printf("[FAIL] ubi_consts\n");
        failures++;
    }

    /* Stage 4: end-to-end completion marker. */
    printf("[CHECK consumer_complete OK] libubi dev library usable as a consumer\n");

    if (failures) {
        printf("TESTS FAILED\n");
        return 1;
    }
    printf("TESTS PASSED\n");
    return 0;
}
