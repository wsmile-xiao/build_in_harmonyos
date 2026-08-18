/*
 * Test source for libquvi-scripts 0.9.20131130
 *
 * Verifies that the Lua scripts package is installed correctly.
 * Takes the package folder path as argv[1].
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

int main(int argc, char *argv[]) {
    if (argc < 2) {
        fprintf(stderr, "Usage: %s <package_folder>\n", argv[0]);
        return 1;
    }
    const char *pkg = argv[1];
    char path[512];
    int ret = 0;

    /* Check share/libquvi-scripts/ directory */
    snprintf(path, sizeof(path), "%s/share/libquvi-scripts", pkg);
    if (!dir_exists(path)) {
        snprintf(path, sizeof(path), "%s/res/share/libquvi-scripts", pkg);
    }
    if (!dir_exists(path)) {
        fprintf(stderr, "FAIL: libquvi-scripts share dir not found in %s\n", pkg);
        return 1;
    }
    printf("PASS: share/libquvi-scripts directory found\n");

    /* Check version symlink (0.9 -> 0.9.20131130) */
    snprintf(path, sizeof(path), "%s/share/libquvi-scripts/0.9", pkg);
    if (!dir_exists(path)) {
        snprintf(path, sizeof(path), "%s/res/share/libquvi-scripts/0.9", pkg);
    }
    if (!dir_exists(path)) {
        fprintf(stderr, "FAIL: version 0.9 directory not found\n");
        return 1;
    }
    printf("PASS: version 0.9 directory found\n");

    /* Check version file */
    snprintf(path, sizeof(path), "%s/share/libquvi-scripts/0.9/version", pkg);
    if (!file_exists(path)) {
        snprintf(path, sizeof(path), "%s/res/share/libquvi-scripts/0.9/version", pkg);
    }
    if (!file_exists(path)) {
        fprintf(stderr, "FAIL: version file not found\n");
        return 1;
    }
    printf("PASS: version file exists\n");

    /* Check key Lua scripts */
    const char *scripts[] = {"const.lua", "html.lua", "util.lua"};
    for (int i = 0; i < 3; i++) {
        snprintf(path, sizeof(path),
                 "%s/share/libquvi-scripts/0.9/common/quvi/%s", pkg, scripts[i]);
        if (!file_exists(path)) {
            snprintf(path, sizeof(path),
                     "%s/res/share/libquvi-scripts/0.9/common/quvi/%s",
                     pkg, scripts[i]);
        }
        if (!file_exists(path)) {
            fprintf(stderr, "FAIL: script %s not found\n", scripts[i]);
            return 1;
        }
    }
    printf("PASS: key Lua scripts (const.lua, html.lua, util.lua) verified\n");

    /* Check media scripts directory has content */
    snprintf(path, sizeof(path), "%s/share/libquvi-scripts/0.9/media", pkg);
    if (!dir_exists(path)) {
        snprintf(path, sizeof(path), "%s/res/share/libquvi-scripts/0.9/media", pkg);
    }
    if (!dir_exists(path)) {
        fprintf(stderr, "FAIL: media scripts directory not found\n");
        return 1;
    }
    printf("PASS: media scripts directory exists\n");

    printf("\nAll libquvi-scripts tests passed.\n");
    return 0;
}
