/*
 * Test for lxqt-menu-data package — verifies that the installed data
 * files (XDG .menu definitions and desktop-directories) actually exist.
 *
 * lxqt-menu-data is a pure data package (no libraries); this test
 * checks the files installed by the recipe. MENU_DATA_DIR is the
 * installed share/ directory, passed by the test_package recipe.
 */
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <unistd.h>
#include <dirent.h>
#include <sys/stat.h>

#ifndef MENU_DATA_DIR
#error "MENU_DATA_DIR must be defined (path to installed share/ dir)"
#endif

static int checks = 0;
static int passed = 0;

#define CHECK(cond, msg) do {              \
    checks++;                              \
    if (cond) { passed++; }                \
    else {                                 \
        fprintf(stderr, "FAIL: %s\n", msg);\
        return 1;                          \
    }                                      \
} while (0)

int main(void)
{
    const char *menu_files[] = {
        "menus/lxqt-applications.menu",
        "menus/lxqt-applications-compact.menu",
        "menus/lxqt-applications-fm.menu",
        "menus/lxqt-config.menu",
        "menus/lxqt-panel-applications.menu",
        NULL
    };
    char path[1024];
    int i;

    /* 1. Every .menu definition must exist and be readable */
    for (i = 0; menu_files[i]; i++) {
        snprintf(path, sizeof(path), "%s/%s", MENU_DATA_DIR, menu_files[i]);
        CHECK(access(path, R_OK) == 0, menu_files[i]);
    }

    /* 2. desktop-directories dir must exist with at least 20 entries */
    snprintf(path, sizeof(path), "%s/desktop-directories", MENU_DATA_DIR);
    struct stat st;
    CHECK(stat(path, &st) == 0 && S_ISDIR(st.st_mode),
          "desktop-directories dir exists");

    DIR *d = opendir(path);
    CHECK(d != NULL, "desktop-directories readable");
    if (d) {
        int npdf = 0;
        struct dirent *e;
        while ((e = readdir(d)) != NULL) {
            if (strstr(e->d_name, ".directory")) npdf++;
        }
        closedir(d);
        CHECK(npdf >= 20, ">=20 .directory files present");
        printf("desktop-directories: %d files\n", npdf);
    }

    /* 3. A known .directory file must exist */
    snprintf(path, sizeof(path), "%s/desktop-directories/lxqt-development.directory",
             MENU_DATA_DIR);
    CHECK(access(path, R_OK) == 0, "lxqt-development.directory exists");

    printf("lxqt-menu-data data test: %d/%d passed\n", passed, checks);
    return (passed == checks) ? 0 : 1;
}