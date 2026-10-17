/* HarmonyOS/OHOS specific consumer test for the libfvde Conan package.
 *
 * Verifies platform properties that only exist on the OHOS target:
 *   * the consumer is really compiled for HarmonyOS (__OHOS__),
 *   * the packaged library reports the adapted upstream version,
 *   * TMPDIR is a writable non-/tmp directory (the device /tmp is read-only),
 *   * a temporary file can be created, written, read back and removed there.
 */
#ifndef __OHOS__
#error "test_ohos.c must be compiled for HarmonyOS"
#endif

#include <libfvde.h>

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
    const char marker[] = "libfvde-ohos";
    char path[4096];
    char buffer[sizeof(marker)] = {0};
    int descriptor;
    int path_length;
    int assertions = 0;

    if (!check(
            strcmp(libfvde_get_version(), "20240502") == 0,
            "libfvde is not the expected OHOS package")) {
        return 1;
    }
    assertions++;

    tmpdir = getenv("TMPDIR");
    if (!check(
            tmpdir != NULL && tmpdir[0] != '\0' && strcmp(tmpdir, "/tmp") != 0,
            "OHOS test must use a writable TMPDIR instead of /tmp")) {
        return 1;
    }
    assertions++;

    path_length = snprintf(
        path,
        sizeof(path),
        "%s/libfvde-ohos-XXXXXX",
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

    printf(
        "libfvde OHOS-specific test: %d assertions passed\n",
        assertions);
    return 0;
}
