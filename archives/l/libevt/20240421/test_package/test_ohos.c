/* OHOS-specific consumer test for libevt 20240421.
 *
 * Only compiled and run for the __OHOS__ target.  Verifies the package
 * resolves to the expected version on OHOS, and exercises the library
 * under HarmonyOS HMDFS constraints: writable TMPDIR (not /tmp), file
 * creation/write/read/unlink lifecycle, and a signature check API call
 * against a file that lives on HMDFS.
 */
#ifndef __OHOS__
#error "test_ohos.c must be compiled for HarmonyOS"
#endif

#include <libevt.h>

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
    const char marker[] = "libevt-ohos";
    char path[4096];
    char buffer[sizeof(marker)] = {0};
    libevt_error_t *error = NULL;
    int descriptor;
    int result;
    int path_length;
    int assertions = 0;

    /* 1. expected OHOS package version */
    if (!check(
            strcmp(libevt_get_version(), "20240421") == 0,
            "libevt is not the expected OHOS package")) {
        return 1;
    }
    assertions++;

    /* 2. writable TMPDIR instead of /tmp (E002 platform constraint) */
    tmpdir = getenv("TMPDIR");
    if (!check(
            tmpdir != NULL && tmpdir[0] != '\0' && strcmp(tmpdir, "/tmp") != 0,
            "OHOS test must use a writable TMPDIR instead of /tmp")) {
        return 1;
    }
    assertions++;

    /* 3. temporary path construction on HMDFS */
    path_length = snprintf(
        path,
        sizeof(path),
        "%s/libevt-ohos-XXXXXX",
        tmpdir);
    if (!check(
            path_length > 0 && (size_t)path_length < sizeof(path),
            "could not construct the OHOS temporary path")) {
        return 1;
    }
    assertions++;

    /* 4. create + write + read back on HMDFS */
    descriptor = mkstemp(path);
    if (!check(descriptor != -1, "mkstemp failed on HMDFS")) {
        return 1;
    }
    assertions++;

    if (!check(
            write(descriptor, marker, sizeof(marker)) == (ssize_t)sizeof(marker),
            "write to HMDFS temporary file failed")) {
        close(descriptor);
        unlink(path);
        return 1;
    }
    assertions++;

    if (!check(lseek(descriptor, 0, SEEK_SET) == 0, "lseek failed")) {
        close(descriptor);
        unlink(path);
        return 1;
    }
    assertions++;

    if (!check(
            read(descriptor, buffer, sizeof(marker)) == (ssize_t)sizeof(marker)
                && memcmp(buffer, marker, sizeof(marker)) == 0,
            "read back from HMDFS temporary file failed")) {
        close(descriptor);
        unlink(path);
        return 1;
    }
    assertions++;

    close(descriptor);

    /* 5. libevt signature check API on an HMDFS file (must report
     * "not an EVT file" = 0, not a hard error) */
    result = libevt_check_file_signature(path, &error);
    if (!check(
            result == 0 && error == NULL,
            "signature check on non-EVT file misbehaved")) {
        libevt_error_free(&error);
        unlink(path);
        return 1;
    }
    assertions++;

    /* 6. unlink cleanup */
    if (!check(unlink(path) == 0, "unlink failed")) {
        return 1;
    }
    assertions++;

    if (!check(access(path, F_OK) == -1 && errno == ENOENT,
                "file still accessible after unlink")) {
        return 1;
    }
    assertions++;

    printf("test_ohos: %d assertions passed\n", assertions);
    return 0;
}
