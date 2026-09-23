/* libjpeg9 OHOS-specific test: R26 static-only package constraint.
 *
 * Porting decision under test (HarmonyOS PC specific): HarmonyOS PC ships
 * its own system libjpeg, so this adaptation deliberately builds the conan
 * package static-only. The package must install lib/libjpeg.a and must
 * never install a libjpeg.so*, so the adapted library can neither shadow
 * the system shared library nor be shadowed by it.
 *
 * The test binary is gated to os=OHOS in test_package/conanfile.py and
 * asserts, on the device, against the real package folder this consumer
 * linked against:
 *   1. runtime platform is HarmonyOS/OpenHarmony (uname sysname);
 *   2. the package lib directory exists (LIBJPEG9_PKG_LIBDIR, injected by
 *      the test_package generate() from the tested dependency package);
 *   3. lib/libjpeg.a exists, is a non-empty regular file with ar magic;
 *   4. no libjpeg.so* entry exists in the package lib directory;
 *   5. no libjpeg.so is mapped into the consumer process (checked via
 *      /proc/self/maps when readable; skipped otherwise).
 */
#include <dirent.h>
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/utsname.h>

#ifndef LIBJPEG9_PKG_LIBDIR
#define LIBJPEG9_PKG_LIBDIR ""
#endif

static int checks = 0;
static int failures = 0;

static void report(int ok, const char *what) {
    checks++;
    printf("[ohos-static] %s %s\n", ok ? "PASS" : "FAIL", what);
    if (!ok) {
        failures++;
    }
}

static int finish(void) {
    printf("[ohos-static] %d/%d assertions passed\n", checks - failures, checks);
    printf("[ohos-static] OHOS R26 static-only constraint test: %s\n",
           failures ? "FAIL" : "OK");
    return failures ? 1 : 0;
}

int main(void) {
    struct utsname sys_info;
    struct stat st;
    char path[4096];

    /* 1. on-device platform check: this test is only meaningful on OHOS. */
    if (uname(&sys_info) != 0) {
        report(0, "uname() failed - cannot verify OHOS runtime platform");
    } else if (strstr(sys_info.sysname, "Harmony") != NULL ||
               strstr(sys_info.sysname, "OHOS") != NULL) {
        printf("[ohos-static] INFO: uname sysname=%s release=%s\n",
               sys_info.sysname, sys_info.release);
        report(1, "runtime platform is HarmonyOS/OpenHarmony");
    } else {
        printf("[ohos-static] INFO: uname sysname=%s\n", sys_info.sysname);
        report(0, "runtime platform is not HarmonyOS/OpenHarmony");
    }

    /* 2. package lib directory injected from the tested dependency. */
    if (LIBJPEG9_PKG_LIBDIR[0] == '\0') {
        report(0, "LIBJPEG9_PKG_LIBDIR not provided - cannot locate package lib dir");
        return finish();
    }
    if (stat(LIBJPEG9_PKG_LIBDIR, &st) != 0 || !S_ISDIR(st.st_mode)) {
        printf("[ohos-static] INFO: LIBJPEG9_PKG_LIBDIR=%s\n", LIBJPEG9_PKG_LIBDIR);
        report(0, "package lib directory missing - package artifacts broken");
        return finish();
    }
    printf("[ohos-static] INFO: package lib dir=%s\n", LIBJPEG9_PKG_LIBDIR);
    report(1, "package lib directory exists");

    /* 3. static artifact present and real. */
    snprintf(path, sizeof(path), "%s/libjpeg.a", LIBJPEG9_PKG_LIBDIR);
    if (stat(path, &st) != 0 || !S_ISREG(st.st_mode) || st.st_size <= 0) {
        report(0, "lib/libjpeg.a missing or empty - static artifact required on OHOS");
    } else {
        FILE *f = fopen(path, "rb");
        if (!f) {
            report(0, "lib/libjpeg.a not readable");
        } else {
            char magic[8];
            memset(magic, 0, sizeof(magic));
            size_t n = fread(magic, 1, sizeof(magic), f);
            fclose(f);
            if (n == sizeof(magic) && memcmp(magic, "!<arch>\n", 8) == 0) {
                printf("[ohos-static] INFO: %s is %ld bytes\n", path, (long)st.st_size);
                report(1, "lib/libjpeg.a is a non-empty ar static archive");
            } else {
                report(0, "lib/libjpeg.a exists but is not an ar archive");
            }
        }
    }

    /* 4. R26: no shared libjpeg in the package. */
    DIR *d = opendir(LIBJPEG9_PKG_LIBDIR);
    if (!d) {
        report(0, "package lib directory not listable");
    } else {
        struct dirent *e;
        char offender[4096] = "";
        while ((e = readdir(d)) != NULL) {
            if (strncmp(e->d_name, "libjpeg.so", 10) == 0) {
                snprintf(offender, sizeof(offender), "%s/%s",
                         LIBJPEG9_PKG_LIBDIR, e->d_name);
                break;
            }
        }
        closedir(d);
        if (offender[0] != '\0') {
            printf("[ohos-static] INFO: offender=%s\n", offender);
            report(0, "libjpeg.so* found in package - violates OHOS R26 static-only constraint");
        } else {
            report(1, "no libjpeg.so* in package lib dir (R26 static-only holds)");
        }
    }

    /* 5. no shared libjpeg mapped into the consumer process. */
    FILE *maps = fopen("/proc/self/maps", "r");
    if (!maps) {
        printf("[ohos-static] INFO: /proc/self/maps not readable - mapping check skipped\n");
    } else {
        char line[4096];
        int mapped = 0;
        while (fgets(line, sizeof(line), maps) != NULL) {
            if (strstr(line, "libjpeg.so") != NULL) {
                mapped = 1;
                break;
            }
        }
        fclose(maps);
        if (mapped) {
            report(0, "a libjpeg.so is mapped into the consumer process");
        } else {
            report(1, "no libjpeg.so mapped into the consumer process");
        }
    }

    return finish();
}
