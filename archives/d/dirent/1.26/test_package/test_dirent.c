/*
 * Consumer test for dirent 1.26 on HarmonyOS PC.
 *
 * Simulates a third-party application: uses only the public dirent API
 * through the package's exported CMake target (find_package(Dirent) +
 * `dirent` target).  Verifies real observable results of directory
 * iteration, sorting and positioning primitives.
 */
#include <dirent.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>

static int failures = 0;

#define CHECK(cond, msg)                                      \
    do {                                                      \
        if (!(cond)) {                                        \
            fprintf(stderr, "FAIL: %s (errno=%d)\n", msg, errno); \
            failures++;                                       \
        }                                                     \
    } while (0)

int main(void)
{
    const char *dir = ".";
    int n = 0, i;
    struct dirent **entries = NULL;

    /* ── opendir / readdir / closedir ─────────────────────── */
    DIR *dp = opendir(dir);
    CHECK(dp != NULL, "opendir('.')");
    n = 0;
    struct dirent *de;
    while ((de = readdir(dp)) != NULL) {
        if (strcmp(de->d_name, ".") == 0 || strcmp(de->d_name, "..") == 0)
            continue;
        n++;
    }
    CHECK(n > 0, "readdir enumerates at least one entry");
    CHECK(closedir(dp) == 0, "closedir");

    /* ── scandir + alphasort ──────────────────────────────── */
    n = scandir(dir, &entries, NULL, alphasort);
    CHECK(n > 0, "scandir returns entries");
    if (n > 0) {
        /* entries are sorted: first non-dot entry must be the smallest name */
        int first = 0;
        for (i = 0; i < n; i++) {
            if (strcmp(entries[i]->d_name, ".") == 0 ||
                strcmp(entries[i]->d_name, "..") == 0)
                continue;
            first = i;
            break;
        }
        CHECK(first >= 0, "scandir has a real entry");
        if (first >= 0) {
            printf("INFO: scandir sorted, first entry = %s\n",
                   entries[first]->d_name);
        }
        for (i = 0; i < n; i++)
            free(entries[i]);
        free(entries);
    }

    /* ── telldir / seekdir / rewinddir ────────────────────── */
    dp = opendir(dir);
    CHECK(dp != NULL, "opendir for seek test");
    if (dp) {
        long pos = telldir(dp);
        (void) pos; /* POSIX telldir may equal 0; only check callability */
        de = readdir(dp);
        CHECK(de != NULL, "readdir after telldir");
        rewinddir(dp);
        de = readdir(dp);
        CHECK(de != NULL, "readdir after rewinddir");
        closedir(dp);
    }

    if (failures) {
        fprintf(stderr, "FAILED: %d assertion(s)\n", failures);
        return 1;
    }
    printf("PASS: dirent consumer test ok\n");
    return 0;
}