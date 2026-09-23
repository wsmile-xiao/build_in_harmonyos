#ifndef __OHOS__
#error "test_ohos.c must be compiled for HarmonyOS"
#endif

#include <libvhdi.h>

#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

static int check(int condition, const char *message)
{
    if (!condition) {
        fprintf(stderr, "FAIL: %s\n", message);
        return 0;
    }
    return 1;
}

int main(void)
{
    const char *tmpdir;
    const char marker[] = "libvhdi-ohos";
    unsigned char image[1024] = {0};
    char path[4096];
    char signature_path[4096];
    char buffer[sizeof(marker)] = {0};
    int descriptor;
    int path_length;
    int signature_descriptor;
    int signature_length;
    int result;
    int assertions = 0;
    libvhdi_error_t *error = NULL;

    if (!check(
            strcmp(libvhdi_get_version(), "20251119") == 0,
            "libvhdi is not the expected OHOS package")) {
        return 1;
    }
    assertions++;

    /* HarmonyOS mounts /tmp read-only, so the device shell injects a writable
     * TMPDIR. On hosts where /tmp is writable that condition does not exist:
     * fall back to a writable directory and report the check as a
     * host-conditional SKIP (never counted as a pass) - same convention as
     * archives/c/cronic/3/test_package/test_cronic_ohos.sh (OHOS-6).
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
        assertions++;
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
        "%s/libvhdi-ohos-XXXXXX",
        tmpdir);
    if (!check(
            path_length > 0 && (size_t)path_length < sizeof(path),
            "could not construct the OHOS temporary path")) {
        return 1;
    }
    assertions++;

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
    assertions++;

    close(descriptor);
    errno = 0;
    if (!check(
            unlink(path) == 0 && access(path, F_OK) != 0 && errno == ENOENT,
            "OHOS temporary file cleanup failed")) {
        return 1;
    }
    assertions++;

    /* Positive consumer path: libvhdi only probes for the signatures when the
     * file is LARGER than 512 bytes, so the fixture is a 1024-byte image whose
     * final 512-byte block starts with the "conectix" VHD (version 1) cookie
     * at offset 512. The packaged library must recognize it.
     */
    memcpy(image + 512, "conectix", 8);
    signature_length = snprintf(
        signature_path,
        sizeof(signature_path),
        "%s/libvhdi-ohos-signature-XXXXXX",
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
            "mkstemp failed for the VHD signature fixture")) {
        return 1;
    }
    if (!check(
            write(signature_descriptor, image, sizeof(image))
                    == (ssize_t)sizeof(image)
                && close(signature_descriptor) == 0,
            "could not write the VHD signature fixture")) {
        close(signature_descriptor);
        unlink(signature_path);
        return 1;
    }
    result = libvhdi_check_file_signature(signature_path, &error);
    if (!check(
            result == 1 && error == NULL,
            "packaged libvhdi did not recognize the VHD footer signature")) {
        libvhdi_error_free(&error);
        unlink(signature_path);
        return 1;
    }
    assertions++;
    unlink(signature_path);

    printf(
        "libvhdi OHOS-specific test: %d assertions passed\n",
        assertions);
    return 0;
}
