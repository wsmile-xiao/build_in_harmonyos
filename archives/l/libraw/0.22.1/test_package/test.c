/* test_package/test.c — LibRaw C API smoke test (R34: substantive API call).
 *
 * Verifies:
 *   - libraw.h can be included
 *   - libraw_init() allocates a handle
 *   - libraw_open_buffer() accepts a tiny synthetic buffer (returns an
 *     error code for non-RAW data, but proves the API is linked and callable)
 *   - libraw_version() returns a non-empty version string
 *   - libraw_strerror() converts an error code to a string
 *   - libraw_recycle() / cleanup run without crash
 *
 * This is a C test (links against libraw, the non-thread-safe variant).
 */
#include <libraw/libraw.h>
#include <stdio.h>
#include <string.h>

int main(void) {
    /* 1. version string must be non-empty */
    const char *ver = libraw_version();
    if (!ver || strlen(ver) == 0) {
        fprintf(stderr, "FAIL: libraw_version() returned empty\n");
        return 1;
    }
    printf("libraw_version: %s\n", ver);

    /* 2. init a LibRaw handle */
    libraw_data_t *lr = libraw_init(LIBRAW_OPTIONS_NONE);
    if (!lr) {
        fprintf(stderr, "FAIL: libraw_init() returned NULL\n");
        return 2;
    }

    /* 3. open_buffer on a small synthetic buffer — will return a non-zero
     *    error code (not a valid RAW), but proves the API symbol is linked. */
    unsigned char buf[64];
    memset(buf, 0, sizeof(buf));
    int rc = libraw_open_buffer(lr, buf, sizeof(buf));
    /* rc != 0 is expected for garbage data; verify strerror works. */
    const char *err = libraw_strerror(rc);
    if (!err || strlen(err) == 0) {
        fprintf(stderr, "FAIL: libraw_strerror(%d) returned empty\n", rc);
        libraw_close(lr);
        return 3;
    }
    printf("open_buffer rc=%d (%s) — expected non-zero for empty buffer\n", rc, err);

    /* 4. recycle (free internal data) then close */
    libraw_recycle(lr);
    libraw_close(lr);

    /* 5. version number (numeric) */
    int vnum = libraw_versionNumber();
    printf("libraw_versionNumber: %d\n", vnum);
    if (vnum <= 0) {
        fprintf(stderr, "FAIL: libraw_versionNumber() <= 0\n");
        return 4;
    }

    printf("LibRaw test_package: ALL CHECKS PASSED\n");
    return 0;
}
