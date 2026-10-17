/*
 * HarmonyOS-specific runtime test #2 for kea-hook-ha.
 *
 * The plug-in is a dlopen()-ed Kea hook, so what must work on HarmonyOS is not
 * only its own load but the whole runtime closure it drags in: the package
 * ships 20 Kea shared libraries (lib/libkea-*.so*), and the OHOS loader has to
 * resolve every DT_NEEDED edge of that closure at run time.  glibc and bionic
 * differ from musl here (rpath handling, soname symlinks, libc++ runtime), so
 * this behaviour is platform specific.
 *
 * Checks
 *   1. every real libkea-*.so* file in <package>/lib loads with RTLD_NOW
 *   2. the count of distinct library base names is >= 20 (the packaged
 *      closure; soname copies would otherwise over-count plain files)
 *   3. no library failed to load (each failure prints its dlerror())
 *   4. after the closure is resident, the hook itself still loads with
 *      RTLD_NOW (its NEEDED closure is fully resolvable)
 *
 * Usage: test_ohos_runtime <path-to-libdhcp_ha.so>
 * Exits non-zero on any failed check.
 */
#include <dirent.h>
#include <dlfcn.h>
#include <libgen.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>

#define EXPECTED_MIN_KEA_LIBS 20
#define MAX_FILES 512
#define MAX_LIBS 64
#define LIBNAME_MAX 128

static int failures = 0;

static void check(int cond, const char *what) {
    if (cond) {
        printf("ok   - %s\n", what);
    } else {
        printf("FAIL - %s\n", what);
        failures++;
    }
    fflush(stdout);
}

static int is_kea_lib(const char *name) {
    return strncmp(name, "libkea-", 7) == 0 && strstr(name, ".so") != NULL;
}

int main(int argc, char **argv) {
    char buf1[4096], buf2[4096], buf3[4096];
    char libdir_buf[4096];
    const char *libdir;
    DIR *dir;
    struct dirent *entry;
    int nreal = 0, nloaded = 0;
    int i;
    void *handles[MAX_FILES];
    void *hook;
    /* distinct "libkea-X" base names seen (the ".so*" suffix dropped) */
    static char bases[MAX_LIBS][LIBNAME_MAX];
    int nbases = 0;

    if (argc != 2) {
        fprintf(stderr, "usage: %s <path-to-libdhcp_ha.so>\n", argv[0]);
        return 2;
    }

    /* <pkg>/lib/kea/hooks/libdhcp_ha.so -> <pkg>/lib */
    snprintf(buf1, sizeof(buf1), "%s", argv[1]);
    snprintf(buf2, sizeof(buf2), "%s", dirname(buf1));
    snprintf(buf3, sizeof(buf3), "%s", dirname(buf2));
    snprintf(libdir_buf, sizeof(libdir_buf), "%s", dirname(buf3));
    libdir = libdir_buf;
    printf("info - packaged Kea runtime lib dir: %s\n", libdir);

    dir = opendir(libdir);
    if (dir == NULL) {
        perror("opendir");
        return 2;
    }

    while ((entry = readdir(dir)) != NULL) {
        char full[4096];
        struct stat st;
        void *handle;

        if (!is_kea_lib(entry->d_name)) {
            continue;
        }
        snprintf(full, sizeof(full), "%s/%s", libdir, entry->d_name);
        if (lstat(full, &st) != 0) {
            continue;
        }
        if (S_ISLNK(st.st_mode)) {
            /* the soname symlinks are covered by loading the real file */
            continue;
        }
        /* check the cap before counting so nreal always matches nloaded */
        if (nreal >= MAX_FILES) {
            break;
        }
        nreal++;
        /* Count the library base name once ("libkea-X.so.3" and
         * "libkea-X.so.3.0.3" are the same library).  OHOS denies symlinks,
         * so the package ships each soname as a real copy and the plain file
         * count alone could over-state the distinct closure. */
        {
            const char *socut = strstr(entry->d_name, ".so");
            if (socut != NULL && (socut - entry->d_name) < LIBNAME_MAX) {
                size_t blen = (size_t)(socut - entry->d_name);
                int seen = 0;
                int b;
                for (b = 0; b < nbases; ++b) {
                    if (strlen(bases[b]) == blen &&
                        strncmp(bases[b], entry->d_name, blen) == 0) {
                        seen = 1;
                        break;
                    }
                }
                if (!seen && nbases < MAX_LIBS) {
                    memcpy(bases[nbases], entry->d_name, blen);
                    bases[nbases][blen] = '\0';
                    nbases++;
                }
            }
        }
        handle = dlopen(full, RTLD_NOW | RTLD_LOCAL);
        if (handle != NULL) {
            printf("ok   - OHOS loader dlopen(RTLD_NOW): %s\n", entry->d_name);
            handles[nloaded++] = handle;
        } else {
            printf("FAIL - OHOS loader dlopen(RTLD_NOW): %s -> %s\n",
                   entry->d_name, dlerror());
            failures++;
        }
    }
    closedir(dir);

    check(nbases >= EXPECTED_MIN_KEA_LIBS,
          "packaged Kea runtime closure present (>= 20 distinct libraries)");
    check(nloaded == nreal,
          "every packaged Kea runtime library loads under the OHOS loader");
    printf("info - Kea runtime libraries: %d distinct, %d files, %d loaded\n",
           nbases, nreal, nloaded);

    hook = dlopen(argv[1], RTLD_NOW | RTLD_LOCAL);
    check(hook != NULL,
          "hook still loads with RTLD_NOW after the closure is resident");
    if (hook != NULL) {
        check(dlsym(hook, "load") != NULL && dlsym(hook, "unload") != NULL,
              "hook contract symbols (load/unload) resolvable at runtime");
        dlclose(hook);
    } else {
        fprintf(stderr, "dlopen(%s) failed: %s\n", argv[1], dlerror());
    }

    /* Release the closure handles so every dlopen() is paired with a
     * dlclose() (the process is short-lived, but keep the pairing complete). */
    for (i = 0; i < nloaded; ++i) {
        dlclose(handles[i]);
    }

    if (failures == 0) {
        printf("kea-hook-ha/3.0.3 OHOS runtime closure check OK\n");
        return 0;
    }
    printf("kea-hook-ha/3.0.3 OHOS runtime closure check FAILED (%d check(s))\n",
           failures);
    return 1;
}
