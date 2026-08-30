/*
 * test_sequential_uuids.c — smoke test for the postgresql-sequential-uuids
 * Conan package.
 *
 * Verifies that the packaged sequential_uuids.so is a valid ELF shared
 * library and that the extension control + SQL files are present.
 *
 * The real functional test is pg_regress (make installcheck) driven by
 * test_package/conanfile.py::test() against a live vendored PG 18.3 server.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>

int main(int argc, char *argv[])
{
    int failures = 0;

    /* Path to sequential_uuids.so passed via argv[1] */
    if (argc < 2) {
        fprintf(stderr, "Usage: %s <path-to-sequential_uuids.so>\n", argv[0]);
        return 1;
    }

    const char *so_path = argv[1];
    int fd = open(so_path, O_RDONLY);
    if (fd < 0) {
        fprintf(stderr, "FAIL: cannot open %s: %s\n", so_path, strerror(errno));
        return 1;
    }

    /* Check ELF magic */
    unsigned char magic[4];
    if (read(fd, magic, 4) != 4) {
        fprintf(stderr, "FAIL: cannot read ELF magic from %s\n", so_path);
        close(fd);
        return 1;
    }
    close(fd);

    if (magic[0] != 0x7f || magic[1] != 'E' || magic[2] != 'L' || magic[3] != 'F') {
        fprintf(stderr, "FAIL: %s is not a valid ELF file\n", so_path);
        return 1;
    }
    printf("PASS: %s is a valid ELF shared library\n", so_path);

    /* Check extension files (passed via env or argv) */
    const char *ext_dir = getenv("SEQUENTIAL_UUIDS_EXT_DIR");
    if (ext_dir) {
        char ctrl[4096], sql[4096];
        struct stat st;

        snprintf(ctrl, sizeof(ctrl), "%s/sequential_uuids.control", ext_dir);
        if (stat(ctrl, &st) == 0) {
            printf("PASS: sequential_uuids.control present\n");
        } else {
            fprintf(stderr, "FAIL: sequential_uuids.control missing at %s\n", ctrl);
            failures++;
        }

        snprintf(sql, sizeof(sql), "%s/sequential_uuids--1.0.1.sql", ext_dir);
        if (stat(sql, &st) == 0) {
            printf("PASS: sequential_uuids--1.0.1.sql present\n");
        } else {
            fprintf(stderr, "FAIL: sequential_uuids--1.0.1.sql missing at %s\n", sql);
            failures++;
        }
    }

    if (failures > 0) {
        fprintf(stderr, "FAIL: %d assertion(s) failed\n", failures);
        return 1;
    }

    printf("PASS: all smoke test assertions passed\n");
    return 0;
}
