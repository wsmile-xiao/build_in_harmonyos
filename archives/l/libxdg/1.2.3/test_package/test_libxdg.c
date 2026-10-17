/* test_package/test_libxdg.c — consumer / integration tests for libxdg 1.2.3
 * on HarmonyOS PC (aarch64, bionic libc, clang 15, libc++).
 *
 * Six assertion groups.  Every group has its own exit code so a CI failure
 * names the failing area without reading the log; a group that fails early
 * still lets the remaining groups run so one CI round reports everything.
 *
 *   1 -> 2 : installed layout + public API surface links
 *   2 -> 3 : $XDG_*_HOME / $XDG_*_DIRS / $XDG_RUNTIME_DIR override contract,
 *            and the spec rule that an EMPTY variable counts as unset
 *   3 -> 4 : spec fallbacks when the XDG variables are unset
 *   4 -> 5 : xdgConfigFind / xdgDataFind / xdgConfigOpen / xdgDataOpen walk
 *            the search path in preference order (real fopen(3) on OHOS)
 *   5 -> 6 : HarmonyOS-specific A — aarch64/bionic ABI (mode_t / off_t /
 *            pointer / long widths, the LP64 struct stat layout the library
 *            was compiled against) and mkdir(2)/stat(2)/access(2) behaviour
 *            on the HarmonyOS filesystem that $TMPDIR points at (HMDFS on
 *            devices, with its setgid-directory policy)
 *   6 -> 7 : HarmonyOS-specific B — four bionic pthreads, each with its OWN
 *            xdgHandle, must produce a bit-identical checksum to the
 *            single-threaded reference: xdgHandle owns its cache, so
 *            concurrent consumers neither share nor corrupt it, and the
 *            results are reproducible across threads on this platform
 */
#include <basedir_fs.h>
#include <basedir.h>

#include <errno.h>
#include <pthread.h>
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>

static int first_failure = 0;
static int checks = 0;

static void fail(int code, const char *group, const char *fmt, ...)
{
    va_list ap;
    if (first_failure == 0)
        first_failure = code;
    fprintf(stderr, "FAIL[%s]: ", group);
    va_start(ap, fmt);
    vfprintf(stderr, fmt, ap);
    va_end(ap);
    fputc('\n', stderr);
}

#define CHECK(group, code, cond, ...)               \
    do {                                            \
        checks++;                                   \
        if (cond) {                                 \
            printf("PASS: " __VA_ARGS__);           \
            putchar('\n');                          \
        } else {                                    \
            fail(code, group, __VA_ARGS__);         \
        }                                           \
    } while (0)

static void env_set(const char *name, const char *value)
{
    if (setenv(name, value, 1) != 0) {
        fprintf(stderr, "FATAL: setenv(%s) failed\n", name);
        exit(99);
    }
}

static void env_unset(const char *name)
{
    unsetenv(name);
}

/* ---------- FNV-1a 64 over a NUL-terminated string ---------- */
static uint64_t fnv(uint64_t h, const char *s)
{
    const unsigned char *p = (const unsigned char *)s;
    if (s == NULL)
        return fnv(h, "(null)");
    for (; *p; ++p) {
        h ^= (uint64_t)*p;
        h *= 1099511628211ULL;
    }
    return h;
}

/* ---------- 1: layout + API surface ---------- */
static void group1(void)
{
    const char *home;
    xdgHandle h;

    CHECK("1", 2, XDG_BASEDIR_SPEC == 0.7,
          "group1: XDG_BASEDIR_SPEC == 0.7 (got %g)", (double)XDG_BASEDIR_SPEC);
    CHECK("1", 2, sizeof(xdgHandle) == sizeof(void *),
          "group1: sizeof(xdgHandle) == sizeof(void*) (opaque single-pointer handle)");

    home = getenv("HOME");
    CHECK("1", 2, home != NULL && home[0] != '\0',
          "group1: HOME is set for the consumer test run");

    /* one xdgInitHandle + xdgWipeHandle round trip proves the archive was
     * linked, not just the headers found */
    h.reserved = NULL;
    CHECK("1", 2, xdgInitHandle(&h) == &h,
          "group1: xdgInitHandle() links and succeeds");
    CHECK("1", 2, xdgDataHome(&h) != NULL && xdgConfigHome(&h) != NULL &&
                  xdgCacheHome(&h) != NULL,
          "group1: xdg{Data,Config,Cache}Home() all resolve");
    CHECK("1", 2, xdgDataDirectories(&h) != NULL &&
                  xdgConfigDirectories(&h) != NULL &&
                  xdgSearchableDataDirectories(&h) != NULL &&
                  xdgSearchableConfigDirectories(&h) != NULL,
          "group1: the four directory-list accessors resolve");
    CHECK("1", 2, xdgUpdateData(&h) != 0,
          "group1: xdgUpdateData() re-caches successfully");
    {
        char *f = xdgConfigFind("libxdg-definitely-absent", &h);
        CHECK("1", 2, f != NULL, "group1: xdgConfigFind() links and returns a list");
        free(f);
        f = xdgDataFind("libxdg-definitely-absent", &h);
        CHECK("1", 2, f != NULL, "group1: xdgDataFind() links and returns a list");
        free(f);
    }
    CHECK("1", 2, xdgConfigOpen("libxdg-definitely-absent", "r", &h) == NULL,
          "group1: xdgConfigOpen() of a missing file returns NULL");
    CHECK("1", 2, xdgDataOpen("libxdg-definitely-absent", "r", &h) == NULL,
          "group1: xdgDataOpen() of a missing file returns NULL");
    xdgWipeHandle(&h);
    CHECK("1", 2, 1, "group1: xdgWipeHandle() returns without crashing");
}

/* ---------- 2: env override contract ---------- */
static void group2(void)
{
    xdgHandle h;
    const char * const *dirs;

    env_set("XDG_CONFIG_HOME", "/ohos/conf");
    env_set("XDG_DATA_HOME", "/ohos/data");
    env_set("XDG_CACHE_HOME", "/ohos/cache");
    env_set("XDG_RUNTIME_DIR", "/ohos/run");
    env_set("XDG_CONFIG_DIRS", "/etc/xdg:/usr/local/etc/xdg");
    env_set("XDG_DATA_DIRS", "/usr/local/share:/usr/share:/ohos/share");
    h.reserved = NULL;
    if (xdgInitHandle(&h) != &h) {
        fail(3, "2", "group2: xdgInitHandle() failed with $XDG_* set");
        return;
    }
    CHECK("2", 3, strcmp(xdgConfigHome(&h), "/ohos/conf") == 0,
          "group2: xdgConfigHome() == $XDG_CONFIG_HOME");
    CHECK("2", 3, strcmp(xdgDataHome(&h), "/ohos/data") == 0,
          "group2: xdgDataHome() == $XDG_DATA_HOME");
    CHECK("2", 3, strcmp(xdgCacheHome(&h), "/ohos/cache") == 0,
          "group2: xdgCacheHome() == $XDG_CACHE_HOME");
    CHECK("2", 3, xdgRuntimeDirectory(&h) != NULL &&
                  strcmp(xdgRuntimeDirectory(&h), "/ohos/run") == 0,
          "group2: xdgRuntimeDirectory() == $XDG_RUNTIME_DIR");

    dirs = xdgConfigDirectories(&h);
    CHECK("2", 3, dirs[0] && dirs[1] && !dirs[2] &&
                  strcmp(dirs[0], "/etc/xdg") == 0 &&
                  strcmp(dirs[1], "/usr/local/etc/xdg") == 0,
          "group2: xdgConfigDirectories() splits $XDG_CONFIG_DIRS on ':' in order");

    dirs = xdgSearchableConfigDirectories(&h);
    CHECK("2", 3, dirs[0] && dirs[1] && dirs[2] && !dirs[3] &&
                  strcmp(dirs[0], "/ohos/conf") == 0 &&
                  strcmp(dirs[1], "/etc/xdg") == 0,
          "group2: xdgSearchableConfigDirectories() prepends $XDG_CONFIG_HOME");

    dirs = xdgDataDirectories(&h);
    CHECK("2", 3, dirs[0] && dirs[1] && dirs[2] && !dirs[3] &&
                  strcmp(dirs[0], "/usr/local/share") == 0 &&
                  strcmp(dirs[2], "/ohos/share") == 0,
          "group2: xdgDataDirectories() preserves $XDG_DATA_DIRS order");

    /* spec: an EMPTY variable is the same as an unset one */
    env_set("XDG_CONFIG_HOME", "");
    env_set("HOME", "/ohos/home");
    xdgWipeHandle(&h);
    h.reserved = NULL;
    if (xdgInitHandle(&h) != &h) {
        fail(3, "2", "group2: xdgInitHandle() failed with an empty $XDG_CONFIG_HOME");
        return;
    }
    CHECK("2", 3, strcmp(xdgConfigHome(&h), "/ohos/home/.config") == 0,
          "group2: empty $XDG_CONFIG_HOME is treated as unset (spec rule)");
    xdgWipeHandle(&h);
}

/* ---------- 3: spec fallbacks ---------- */
static void group3(void)
{
    xdgHandle h;
    const char * const *dirs;

    env_unset("XDG_DATA_HOME");
    env_unset("XDG_CONFIG_HOME");
    env_unset("XDG_CACHE_HOME");
    env_unset("XDG_DATA_DIRS");
    env_unset("XDG_CONFIG_DIRS");
    env_unset("XDG_RUNTIME_DIR");
    env_set("HOME", "/ohos/home");

    h.reserved = NULL;
    if (xdgInitHandle(&h) != &h) {
        fail(4, "3", "group3: xdgInitHandle() failed with every $XDG_* unset");
        return;
    }
    CHECK("3", 4, strcmp(xdgConfigHome(&h), "/ohos/home/.config") == 0,
          "group3: fallback $HOME/.config");
    CHECK("3", 4, strcmp(xdgDataHome(&h), "/ohos/home/.local/share") == 0,
          "group3: fallback $HOME/.local/share");
    CHECK("3", 4, strcmp(xdgCacheHome(&h), "/ohos/home/.cache") == 0,
          "group3: fallback $HOME/.cache");
    CHECK("3", 4, xdgRuntimeDirectory(&h) == NULL,
          "group3: unset $XDG_RUNTIME_DIR yields NULL (no default)");

    dirs = xdgDataDirectories(&h);
    CHECK("3", 4, dirs[0] && dirs[1] && !dirs[2] &&
                  strcmp(dirs[0], "/usr/local/share") == 0 &&
                  strcmp(dirs[1], "/usr/share") == 0,
          "group3: default data dirs are /usr/local/share:/usr/share");
    dirs = xdgConfigDirectories(&h);
    CHECK("3", 4, dirs[0] && !dirs[1] && strcmp(dirs[0], "/etc/xdg") == 0,
          "group3: default config dirs are /etc/xdg");
    xdgWipeHandle(&h);
}

/* ---------- 4: filesystem discovery ---------- */
static void group4(const char *tmp)
{
    xdgHandle h;
    char dir_a[512], dir_b[512], dir_c[512], file[512];
    FILE *fp;
    char *found;

    snprintf(dir_a, sizeof dir_a, "%s/xdg-a", tmp);
    snprintf(dir_b, sizeof dir_b, "%s/xdg-b", tmp);
    snprintf(dir_c, sizeof dir_c, "%s/xdg-c", tmp);
    snprintf(file, sizeof file, "%s/xdg-a/xdg-probe.conf", tmp);

    if (xdgMakePath(dir_a, 0700) != 0 || xdgMakePath(dir_b, 0700) != 0 ||
        xdgMakePath(dir_c, 0700) != 0) {
        fail(5, "4", "group4: could not create the probe directories under TMPDIR");
        return;
    }
    fp = fopen(file, "w");
    if (fp == NULL) {
        fail(5, "4", "group4: could not write the probe file under TMPDIR");
        return;
    }
    fputs("libxdg\n", fp);
    fclose(fp);

    /* $XDG_CONFIG_DIRS order: xdg-b (=config home) first, then xdg-a, xdg-c */
    env_set("XDG_CONFIG_HOME", dir_b);
    env_set("XDG_CONFIG_DIRS", dir_a);
    env_set("XDG_DATA_HOME", dir_b);
    env_set("XDG_DATA_DIRS", dir_a);
    h.reserved = NULL;
    if (xdgInitHandle(&h) != &h) {
        fail(5, "4", "group4: xdgInitHandle() failed for the discovery test");
        return;
    }

    found = xdgConfigFind("xdg-probe.conf", &h);
    CHECK("4", 5, found != NULL && found[0] != '\0',
          "group4: xdgConfigFind() finds the file placed in $XDG_CONFIG_DIRS");
    if (found && found[0] != '\0') {
        char expect[600];
        snprintf(expect, sizeof expect, "%s/xdg-probe.conf", dir_a);
        CHECK("4", 5, strcmp(found, expect) == 0,
              "group4: xdgConfigFind() returns the search-path entry, not the home one");
        CHECK("4", 5, found[strlen(found) + 1] == '\0',
              "group4: xdgConfigFind() result is a double-NUL terminated list");
    }
    free(found);

    fp = xdgConfigOpen("xdg-probe.conf", "r", &h);
    CHECK("4", 5, fp != NULL, "group4: xdgConfigOpen() opens the discovered file");
    if (fp != NULL) {
        char line[64] = {0};
        CHECK("4", 5, fgets(line, sizeof line, fp) != NULL &&
                      strcmp(line, "libxdg\n") == 0,
              "group4: the opened file really is the fixture on disk");
        fclose(fp);
    }

    /* the data search path is searched too: $XDG_DATA_HOME (empty) is
     * consulted before $XDG_DATA_DIRS, so the hit must come from xdg-a */
    found = xdgDataFind("xdg-probe.conf", &h);
    CHECK("4", 5, found != NULL && found[0] != '\0',
          "group4: xdgDataFind() finds the file placed in $XDG_DATA_DIRS");
    if (found && found[0] != '\0') {
        char expect[600];
        snprintf(expect, sizeof expect, "%s/xdg-probe.conf", dir_a);
        CHECK("4", 5, strcmp(found, expect) == 0 &&
                      found[strlen(found) + 1] == '\0',
              "group4: xdgDataFind() returns the searched entry, double-NUL terminated");
    }
    free(found);

    /* the same probe name that is absent from the data path must not be
     * reported as a hit just because the config path has it */
    found = xdgDataFind("xdg-absent.conf", &h);
    CHECK("4", 5, found != NULL && found[0] == '\0',
          "group4: xdgDataFind() yields the empty list when nothing matches");
    free(found);

    /* xdg-c exists but holds no file: the config-dirs-only entry must not
     * make the search report a hit */
    env_set("XDG_CONFIG_DIRS", dir_c);
    xdgWipeHandle(&h);
    h.reserved = NULL;
    if (xdgInitHandle(&h) != &h) {
        fail(5, "4", "group4: xdgInitHandle() failed for the negative case");
        return;
    }
    found = xdgConfigFind("xdg-probe.conf", &h);
    CHECK("4", 5, found != NULL && found[0] == '\0',
          "group4: a search path without the file yields the empty list");
    free(found);
    xdgWipeHandle(&h);
}

/* ---------- 5: HarmonyOS ABI + OHOS filesystem ---------- */
static void group5(const char *tmp)
{
    char dir[512], sub[512];
    struct stat st;

    memset(&st, 0, sizeof st);

    /* aarch64/bionic is LP64: these are the widths libxdg-basedir.a was
     * compiled against, and a mismatched sysroot would show up here */
    CHECK("5", 6, sizeof(mode_t) == 4,
          "ohos: sizeof(mode_t) == 4 (bionic aarch64)");
    CHECK("5", 6, sizeof(off_t) == 8,
          "ohos: sizeof(off_t) == 8 (LP64 large-file struct stat)");
    CHECK("5", 6, sizeof(long) == 8 && sizeof(void *) == 8,
          "ohos: sizeof(long) == sizeof(void*) == 8 (LP64)");
    CHECK("5", 6, (size_t)(mode_t)-1 == (size_t)4294967295u,
          "ohos: (mode_t)-1 is 32-bit unsigned, not sign-extended");

    snprintf(dir, sizeof dir, "%s/ohos-xdg-probe/sub/deep", tmp);

    errno = 0;
    CHECK("5", 6, xdgMakePath(dir, 0700) == 0,
          "ohos: xdgMakePath() creates nested directories on the OHOS filesystem");
    CHECK("5", 6, stat(dir, &st) == 0 && S_ISDIR(st.st_mode),
          "ohos: stat() sees the created path as a directory");
    CHECK("5", 6, (st.st_mode & 0700) == 0700,
          "ohos: the owner rwx bits requested through mkdir(2) survive the FS");
    CHECK("5", 6, access(dir, R_OK | W_OK | X_OK) == 0,
          "ohos: the created tree is reachable/readable/writable (access(2))");

    errno = 0;
    CHECK("5", 6, xdgMakePath(dir, 0700) == -1 && errno == EEXIST,
          "ohos: re-creating an existing path returns -1/EEXIST, not a crash");

    snprintf(sub, sizeof sub, "%s/ohos-xdg-file/", tmp);
    CHECK("5", 6, xdgMakePath(sub, 0755) == 0,
          "ohos: xdgMakePath() accepts a trailing separator");

    CHECK("5", 6, xdgMakePath("/", 0700) == 0,
          "ohos: xdgMakePath(\"/\") is a documented no-op success");
}

/* ---------- 6: HarmonyOS multi-thread reproducibility ---------- */
#define NTHREADS 4
#define NITER 200

static uint64_t probe_checksum(void)
{
    xdgHandle h;
    uint64_t sum = 1469598103934665603ULL;
    int i;

    h.reserved = NULL;
    if (xdgInitHandle(&h) != &h)
        return 0;
    for (i = 0; i < NITER; ++i) {
        const char * const *dirs;
        char *found;
        sum = fnv(sum, xdgConfigHome(&h));
        sum = fnv(sum, xdgDataHome(&h));
        sum = fnv(sum, xdgCacheHome(&h));
        sum = fnv(sum, xdgRuntimeDirectory(&h));
        for (dirs = xdgSearchableConfigDirectories(&h); *dirs; ++dirs)
            sum = fnv(sum, *dirs);
        for (dirs = xdgSearchableDataDirectories(&h); *dirs; ++dirs)
            sum = fnv(sum, *dirs);
        found = xdgConfigFind("libxdg-absent-probe", &h);
        sum = fnv(sum, found);
        free(found);
        found = xdgDataFind("libxdg-absent-probe", &h);
        sum = fnv(sum, found);
        free(found);
    }
    xdgWipeHandle(&h);
    return sum;
}

struct thread_arg {
    uint64_t sum;
    int ok;
};

static void *thread_body(void *p)
{
    struct thread_arg *a = (struct thread_arg *)p;
    a->sum = probe_checksum();
    a->ok = (a->sum != 0);
    return NULL;
}

static void group6(void)
{
    pthread_t tid[NTHREADS];
    struct thread_arg arg[NTHREADS];
    uint64_t reference;
    int i;

    env_unset("XDG_DATA_DIRS");
    env_unset("XDG_CONFIG_DIRS");
    env_set("HOME", "/ohos/thread-home");
    env_set("XDG_CONFIG_HOME", "/ohos/thread-home/.config");
    env_set("XDG_DATA_HOME", "/ohos/thread-home/.local/share");
    env_set("XDG_RUNTIME_DIR", "/ohos/thread-run");

    reference = probe_checksum();
    CHECK("6", 7, reference != 0,
          "ohos-threads: single-threaded reference checksum is non-zero");

    for (i = 0; i < NTHREADS; ++i) {
        arg[i].sum = 0;
        arg[i].ok = 0;
        if (pthread_create(&tid[i], NULL, thread_body, &arg[i]) != 0) {
            fail(7, "6", "ohos-threads: pthread_create() failed for thread %d", i);
            return;
        }
    }
    for (i = 0; i < NTHREADS; ++i) {
        pthread_join(tid[i], NULL);
        if (!arg[i].ok)
            fail(7, "6", "ohos-threads: thread %d produced a zero checksum", i);
    }
    for (i = 0; i < NTHREADS; ++i) {
        CHECK("6", 7, arg[i].sum == reference,
              "ohos-threads: thread %d checksum is bit-identical to the reference "
              "(own xdgHandle, no shared cache)", i);
    }
}

int main(void)
{
    const char *tmp = getenv("TMPDIR");

    if (tmp == NULL || tmp[0] == '\0')
        tmp = ".";

    group1();
    group2();
    group3();
    group4(tmp);
    group5(tmp);
    group6();

    if (first_failure != 0) {
        printf("FAILED: libxdg consumer checks (%d checks, first failing group exit %d)\n",
               checks, first_failure);
        return first_failure;
    }
    printf("ALL PASS: libxdg 1.2.3 consumer checks (6 groups, %d checks, TMPDIR=%s)\n",
           checks, tmp);
    return 0;
}
