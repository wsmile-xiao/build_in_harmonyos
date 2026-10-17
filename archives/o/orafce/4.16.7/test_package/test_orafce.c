/*
 * test_orafce.c — Smoke test for orafce package.
 * Verifies that orafce.so exists and is a valid ELF shared library.
 * The full Oracle-compat functional test is driven by pg_regress in
 * test_package/conanfile.py (including the injected harmonyos_feasibility
 * HarmonyOS consumer-feasibility case).
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>

int main(int argc, char *argv[])
{
    const char *pkg_dir = getenv("ORAFCE_PACKAGE_DIR");
    if (!pkg_dir) {
        if (argc > 1) {
            pkg_dir = argv[1];
        } else {
            fprintf(stderr, "ORAFCE_PACKAGE_DIR not set and no arg given\n");
            return 1;
        }
    }

    char so_path[4096];
    snprintf(so_path, sizeof(so_path), "%s/lib/orafce.so", pkg_dir);

    struct stat st;
    if (stat(so_path, &st) != 0) {
        fprintf(stderr, "FAIL: orafce.so not found at %s\n", so_path);
        return 1;
    }
    printf("PASS: orafce.so exists at %s (%ld bytes)\n", so_path, st.st_size);

    FILE *f = fopen(so_path, "rb");
    if (!f) {
        fprintf(stderr, "FAIL: cannot open %s\n", so_path);
        return 1;
    }
    unsigned char magic[4];
    if (fread(magic, 1, 4, f) != 4) {
        fprintf(stderr, "FAIL: cannot read magic from %s\n", so_path);
        fclose(f);
        return 1;
    }
    fclose(f);

    if (magic[0] != 0x7f || magic[1] != 'E' ||
        magic[2] != 'L' || magic[3] != 'F') {
        fprintf(stderr, "FAIL: orafce.so is not a valid ELF file\n");
        return 1;
    }
    printf("PASS: orafce.so is a valid ELF shared library\n");
    return 0;
}
