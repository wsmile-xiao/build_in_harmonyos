/* HarmonyOS-specific consumer test for the packaged libfshfs.
 *
 * Compile-time guards (2): this file only builds for the OHOS target and only
 * against the packaged version macro.
 * Runtime assertions (10): version string, writable TMPDIR that is not the
 * read-only /tmp, temporary file creation, write/read round trip, cleanup and
 * a positive HFS+ signature probe using a fixture created on the device.
 */
#include <libfshfs.h>

/* Compile-time guards: the OHOS target and the packaged version macro.
 * They are placed after <libfshfs.h> because LIBFSHFS_VERSION lives in
 * <libfshfs/definitions.h>, which the umbrella header pulls in.
 */
#ifndef __OHOS__
#error "test_ohos.c must be compiled for HarmonyOS"
#endif

#if LIBFSHFS_VERSION != 20260130
#error "test_ohos.c must be compiled against libfshfs 20260130"
#endif

#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

static int assertions = 0;

static int check(int condition, const char *message)
{
    if (!condition) {
        fprintf(stderr, "FAIL: %s\n", message);
        return 0;
    }
    assertions++;
    return 1;
}

int main(void)
{
    const char *tmpdir;
    const char marker[] = "libfshfs-ohos";
    unsigned char image[1536];
    char path[4096];
    char signature_path[4096];
    char buffer[sizeof(marker)] = {0};
    int descriptor;
    int path_length;
    int signature_descriptor;
    int signature_length;
    int result;
    libfshfs_error_t *error = NULL;

    if (!check(
            strcmp(libfshfs_get_version(), "20260130") == 0,
            "libfshfs is not the expected OHOS package")) {
        return 1;
    }

    /* HarmonyOS mounts /tmp read-only, so the device shell injects a writable
     * TMPDIR. On hosts where /tmp is writable that condition does not exist:
     * fall back to a writable directory and report the check as a
     * host-conditional SKIP (never counted as a pass) - same convention as
     * archives/l/libvhdi/20251119/test_package/test_ohos.c (OHOS-6).
     */
    tmpdir = getenv("TMPDIR");
    if (access("/tmp", W_OK) != 0) {
        if (!check(
                tmpdir != NULL && tmpdir[0] != '\0'
                    && strcmp(tmpdir, "/tmp") != 0,
                "OHOS device must provide a writable TMPDIR instead of the "
                "read-only /tmp")) {
            return 1;
        }
    } else {
        if (tmpdir == NULL || tmpdir[0] == '\0') {
            tmpdir = ".";
        }
        printf(
            "SKIP: host /tmp is writable; the read-only-/tmp TMPDIR condition "
            "is not exercised here\n");
    }

    path_length = snprintf(
        path,
        sizeof(path),
        "%s/libfshfs-ohos-XXXXXX",
        tmpdir);
    if (!check(
            path_length > 0 && (size_t)path_length < sizeof(path),
            "could not construct the OHOS temporary path")) {
        return 1;
    }

    descriptor = mkstemp(path);
    if (!check(descriptor >= 0, "mkstemp failed under the OHOS TMPDIR")) {
        return 1;
    }
    if (!check(
            write(descriptor, marker, sizeof(marker) - 1)
                    == (ssize_t)(sizeof(marker) - 1)
                && lseek(descriptor, 0, SEEK_SET) == 0
                && read(descriptor, buffer, sizeof(marker) - 1)
                    == (ssize_t)(sizeof(marker) - 1)
                && memcmp(buffer, marker, sizeof(marker) - 1) == 0,
            "OHOS TMPDIR file write/read round trip failed")) {
        close(descriptor);
        unlink(path);
        return 1;
    }

    close(descriptor);
    errno = 0;
    if (!check(
            unlink(path) == 0 && access(path, F_OK) != 0 && errno == ENOENT,
            "OHOS temporary file cleanup failed")) {
        return 1;
    }

    /* Positive consumer path on the device: a 1536-byte fixture whose bytes at
     * offset 1024 carry the HFS+ volume signature must be recognized by the
     * packaged shared library.
     */
    memset(image, 0, sizeof(image));
    memcpy(image + 1024, "H+", 2);
    signature_length = snprintf(
        signature_path,
        sizeof(signature_path),
        "%s/libfshfs-ohos-signature-XXXXXX",
        tmpdir);
    if (!check(
            signature_length > 0
                && (size_t)signature_length < sizeof(signature_path),
            "could not construct the OHOS signature path")) {
        return 1;
    }
    signature_descriptor = mkstemp(signature_path);
    if (!check(
            signature_descriptor >= 0,
            "mkstemp failed for the HFS+ signature fixture")) {
        return 1;
    }
    if (!check(
            write(signature_descriptor, image, sizeof(image))
                    == (ssize_t)sizeof(image)
                && close(signature_descriptor) == 0,
            "could not write the HFS+ signature fixture")) {
        close(signature_descriptor);
        unlink(signature_path);
        return 1;
    }
    result = libfshfs_check_volume_signature(signature_path, &error);
    if (!check(
            result == 1 && error == NULL,
            "packaged libfshfs did not recognize the HFS+ volume signature")) {
        libfshfs_error_free(&error);
        unlink(signature_path);
        return 1;
    }
    unlink(signature_path);

    printf(
        "libfshfs OHOS-specific test: %d assertions passed\n",
        assertions);
    return 0;
}
