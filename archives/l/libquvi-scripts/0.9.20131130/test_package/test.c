/*
 * Test source for libquvi-scripts 0.9.20131130
 *
 * Verifies that the Lua scripts package is installed correctly.
 * Takes the package folder path as argv[1].
 *
 * Checks multiple path variants to handle:
 * - HMDFS symlink issues (0.9 symlink may not resolve via stat())
 * - Conan resdirs relocation (share/ may become res/share/)
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>

static int file_exists(const char *path) {
    struct stat st;
    return stat(path, &st) == 0 && S_ISREG(st.st_mode);
}

static int dir_exists(const char *path) {
    struct stat st;
    return stat(path, &st) == 0 && S_ISDIR(st.st_mode);
}

/* Try path with and without res/ prefix */
static int try_dir(const char *pkg, const char *sub, char *out, size_t sz) {
    snprintf(out, sz, "%s/%s", pkg, sub);
    if (dir_exists(out)) return 1;
    snprintf(out, sz, "%s/res/%s", pkg, sub);
    if (dir_exists(out)) return 1;
    return 0;
}

static int try_file(const char *pkg, const char *sub, char *out, size_t sz) {
    snprintf(out, sz, "%s/%s", pkg, sub);
    if (file_exists(out)) return 1;
    snprintf(out, sz, "%s/res/%s", pkg, sub);
    if (file_exists(out)) return 1;
    return 0;
}

int main(int argc, char *argv[]) {
    if (argc < 2) {
        fprintf(stderr, "Usage: %s <package_folder>\n", argv[0]);
        return 1;
    }
    const char *pkg = argv[1];
    char path[512];

    /* Check share/libquvi-scripts/ directory */
    if (!try_dir(pkg, "share/libquvi-scripts", path, sizeof(path))) {
        fprintf(stderr, "FAIL: libquvi-scripts share dir not found in %s\n", pkg);
        return 1;
    }
    printf("PASS: share/libquvi-scripts directory found\n");

    /* Check version directory (try 0.9 symlink first, then 0.9.20131130 direct)
     * HMDFS may not resolve symlinks via stat() */
    if (!try_dir(pkg, "share/libquvi-scripts/0.9", path, sizeof(path))) {
        if (!try_dir(pkg, "share/libquvi-scripts/0.9.20131130", path, sizeof(path))) {
            fprintf(stderr, "FAIL: version directory not found (tried 0.9 and 0.9.20131130)\n");
            return 1;
        }
    }
    printf("PASS: version directory found\n");

    /* Determine which version dir path works for subsequent checks */
    const char *ver_sub = "share/libquvi-scripts/0.9";
    char ver_path[512];
    snprintf(ver_path, sizeof(ver_path), "%s/share/libquvi-scripts/0.9", pkg);
    if (!dir_exists(ver_path)) {
        snprintf(ver_path, sizeof(ver_path), "%s/res/share/libquvi-scripts/0.9", pkg);
    }
    if (!dir_exists(ver_path)) {
        snprintf(ver_path, sizeof(ver_path), "%s/share/libquvi-scripts/0.9.20131130", pkg);
        ver_sub = "share/libquvi-scripts/0.9.20131130";
        if (!dir_exists(ver_path)) {
            snprintf(ver_path, sizeof(ver_path), "%s/res/share/libquvi-scripts/0.9.20131130", pkg);
        }
    }

    /* Check version file */
    snprintf(path, sizeof(path), "%s/%s/version", pkg, ver_sub);
    if (!file_exists(path)) {
        snprintf(path, sizeof(path), "%s/res/%s/version", pkg, ver_sub);
    }
    if (!file_exists(path)) {
        fprintf(stderr, "FAIL: version file not found\n");
        return 1;
    }
    printf("PASS: version file exists\n");

    /* Check key Lua scripts */
    const char *scripts[] = {"const.lua", "html.lua", "util.lua"};
    for (int i = 0; i < 3; i++) {
        snprintf(path, sizeof(path), "%s/%s/common/quvi/%s", pkg, ver_sub, scripts[i]);
        if (!file_exists(path)) {
            snprintf(path, sizeof(path), "%s/res/%s/common/quvi/%s", pkg, ver_sub, scripts[i]);
        }
        if (!file_exists(path)) {
            fprintf(stderr, "FAIL: script %s not found\n", scripts[i]);
            return 1;
        }
    }
    printf("PASS: key Lua scripts (const.lua, html.lua, util.lua) verified\n");

    /* Check media scripts directory has content */
    snprintf(path, sizeof(path), "%s/%s/media", pkg, ver_sub);
    if (!dir_exists(path)) {
        snprintf(path, sizeof(path), "%s/res/%s/media", pkg, ver_sub);
    }
    if (!dir_exists(path)) {
        fprintf(stderr, "FAIL: media scripts directory not found\n");
        return 1;
    }
    printf("PASS: media scripts directory exists\n");

    /* Check pkg-config file in lib/ directory
     * This ensures the test depends on lib/ (which L1e destructive test sabotages) */
    if (!try_file(pkg, "lib/pkgconfig/libquvi-scripts-0.9.pc", path, sizeof(path))) {
        fprintf(stderr, "FAIL: pkg-config file (libquvi-scripts-0.9.pc) not found\n");
        return 1;
    }
    printf("PASS: pkg-config file exists\n");

    printf("\nAll libquvi-scripts tests passed.\n");
    return 0;
}
