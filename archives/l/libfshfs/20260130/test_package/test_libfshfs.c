/* Consumer test for the packaged libfshfs (generic assertions).
 *
 * Every assertion uses the public API of the installed package: the version
 * string reported by the shared library, the read access flag, the narrow
 * string codepage round trip (including its error path), the HFS / HFS+
 * volume signature probe and the volume lifecycle.
 *
 * Returns 0 when all assertions pass, 1 on the first failure.
 */
#include <libfshfs.h>

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

/* Writes a file whose bytes at offset 1024 carry the given 2-byte signature. */
static int write_signature_fixture(const char *path, const char *signature)
{
    unsigned char buffer[1536];
    FILE *stream;

    memset(buffer, 0, sizeof(buffer));
    memcpy(buffer + 1024, signature, 2);

    stream = fopen(path, "wb");
    if (stream == NULL) {
        return 0;
    }
    if (fwrite(buffer, 1, sizeof(buffer), stream) != sizeof(buffer)) {
        fclose(stream);
        return 0;
    }
    return fclose(stream) == 0;
}

int main(void)
{
    const char *tmpdir;
    char plain_path[4096];
    char hfs_plus_path[4096];
    char hfs_path[4096];
    char missing_path[4096];
    libfshfs_error_t *error = NULL;
    libfshfs_volume_t *volume = NULL;
    int codepage = -1;
    int result;

    tmpdir = getenv("TMPDIR");
    if (tmpdir == NULL || tmpdir[0] == '\0') {
        tmpdir = ".";
    }
    snprintf(plain_path, sizeof(plain_path), "%s/fshfs-consumer-plain", tmpdir);
    snprintf(hfs_plus_path, sizeof(hfs_plus_path), "%s/fshfs-consumer-hfsplus", tmpdir);
    snprintf(hfs_path, sizeof(hfs_path), "%s/fshfs-consumer-hfs", tmpdir);
    snprintf(missing_path, sizeof(missing_path), "%s/fshfs-consumer-missing", tmpdir);
    unlink(missing_path);

    if (!check(
            strcmp(libfshfs_get_version(), "20260130") == 0,
            "libfshfs_get_version() did not report the packaged version")) {
        return 1;
    }
    if (!check(
            libfshfs_get_access_flags_read() == LIBFSHFS_ACCESS_FLAG_READ,
            "libfshfs_get_access_flags_read() did not report the read flag")) {
        return 1;
    }
    if (!check(
            LIBFSHFS_OPEN_READ == LIBFSHFS_ACCESS_FLAG_READ,
            "LIBFSHFS_OPEN_READ does not match the read access flag")) {
        return 1;
    }
    if (!check(
            libfshfs_get_codepage(&codepage, &error) == 1 && codepage == 0
                && error == NULL,
            "libfshfs_get_codepage() did not default to 0")) {
        libfshfs_error_free(&error);
        return 1;
    }
    if (!check(
            libfshfs_set_codepage(1252, &error) == 1
                && libfshfs_get_codepage(&codepage, &error) == 1
                && codepage == 1252,
            "libfshfs_set_codepage(1252) round trip failed")) {
        libfshfs_error_free(&error);
        return 1;
    }
    if (!check(
            libfshfs_set_codepage(0, &error) == 1
                && libfshfs_get_codepage(&codepage, &error) == 1
                && codepage == 0,
            "libfshfs_set_codepage(0) round trip failed")) {
        libfshfs_error_free(&error);
        return 1;
    }
    /* Error path: negative codepage values are rejected with a libfshfs error. */
    error = NULL;
    if (!check(
            libfshfs_set_codepage(-1, &error) == -1 && error != NULL,
            "libfshfs_set_codepage(-1) did not fail with a libfshfs error")) {
        libfshfs_error_free(&error);
        return 1;
    }
    libfshfs_error_free(&error);
    error = NULL;

    /* Signature probes: negative, HFS+ (H+) and HFS (BD) fixtures. */
    if (!write_signature_fixture(plain_path, "NO")) {
        fprintf(stderr, "FAIL: could not write the plain fixture\n");
        return 1;
    }
    if (!check(
            libfshfs_check_volume_signature(plain_path, &error) == 0
                && error == NULL,
            "libfshfs_check_volume_signature() accepted a non-HFS file")) {
        libfshfs_error_free(&error);
        return 1;
    }
    if (!write_signature_fixture(hfs_plus_path, "H+")) {
        fprintf(stderr, "FAIL: could not write the HFS+ fixture\n");
        return 1;
    }
    if (!check(
            libfshfs_check_volume_signature(hfs_plus_path, &error) == 1
                && error == NULL,
            "libfshfs_check_volume_signature() missed the HFS+ signature")) {
        libfshfs_error_free(&error);
        return 1;
    }
    if (!write_signature_fixture(hfs_path, "BD")) {
        fprintf(stderr, "FAIL: could not write the HFS fixture\n");
        return 1;
    }
    if (!check(
            libfshfs_check_volume_signature(hfs_path, &error) == 1
                && error == NULL,
            "libfshfs_check_volume_signature() missed the HFS signature")) {
        libfshfs_error_free(&error);
        return 1;
    }
    /* Error path: a missing file returns -1 and sets a libfshfs error. */
    error = NULL;
    if (!check(
            libfshfs_check_volume_signature(missing_path, &error) == -1
                && error != NULL,
            "libfshfs_check_volume_signature() did not fail on a missing file")) {
        libfshfs_error_free(&error);
        return 1;
    }
    libfshfs_error_free(&error);
    error = NULL;

    /* Volume lifecycle and the open error path on a non-HFS file. */
    if (!check(
            libfshfs_volume_initialize(&volume, &error) == 1 && volume != NULL,
            "libfshfs_volume_initialize() failed")) {
        libfshfs_error_free(&error);
        return 1;
    }
    if (!check(
            libfshfs_volume_open(volume, plain_path, LIBFSHFS_OPEN_READ, &error)
                    == -1
                && error != NULL,
            "libfshfs_volume_open() accepted a non-HFS file")) {
        libfshfs_error_free(&error);
        libfshfs_volume_free(&volume, NULL);
        return 1;
    }
    libfshfs_error_free(&error);
    error = NULL;
    if (!check(
            libfshfs_volume_free(&volume, &error) == 1 && volume == NULL,
            "libfshfs_volume_free() failed")) {
        libfshfs_error_free(&error);
        return 1;
    }

    unlink(plain_path);
    unlink(hfs_plus_path);
    unlink(hfs_path);

    printf("libfshfs consumer test: %d assertions passed\n", assertions);
    return 0;
}
