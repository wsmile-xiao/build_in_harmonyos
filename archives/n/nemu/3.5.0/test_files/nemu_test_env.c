/*
 * nemu_test_env.c - env adaptation layer to run nemu upstream tests on OHOS device.
 *
 * Background (HarmonyOS PC aarch64, measured 2026-09-11):
 *   1. root /tmp is read-only erofs; upstream test/utils.py hardcodes
 *      "/tmp/nemu_<uuid>" workdir (does not read TMPDIR).
 *   2. OHOS has no /etc/passwd; getpwuid() returns NULL and nemu exits
 *      with "Error get home directory".
 *   3. nemu.cfg.in sets qemu_bin_path=/usr/bin; qemu-system-x86_64 and
 *      qemu-img are test stubs (controlled output for the command-line assertions).
 *
 * Adaptation (all driven by env vars; upstream sources and tests untouched):
 *   NEMU_TMP_BASE      - redirect target for /tmp/<x> (must be a writable tmpfs)
 *   NEMU_FAKE_HOME     - fake home dir returned by getpwuid
 *   NEMU_QEMU_STUB_DIR - stub dir for /usr/bin/qemu-* redirection
 *   NEMU_TEST_ENV_DEBUG - non-empty: print redirect details to stderr
 *
 * Pattern follows leptonica 1.85.0 test_files/lept_tmp_redirect.c.
 */
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <dlfcn.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <fcntl.h>
#include <unistd.h>
#include <stdarg.h>
#include <dirent.h>
#include <errno.h>
#include <pwd.h>
#include <sys/statvfs.h>

/* --- env var read (lazy, once) --------------------------- */

__attribute__((constructor))
static void nemu_test_env_ctor(void)
{
    if (getenv("NEMU_TEST_ENV_DEBUG")) {
        dprintf(2, "[nemu-test-env] library loaded into pid=%d\n", getpid());
    }
}

static const char *env_once(const char *name)
{
    return getenv(name);
}

static int dbg_on(void)
{
    static int v = -1;
    if (v < 0) {
        const char *e = getenv("NEMU_TEST_ENV_DEBUG");
        v = (e && e[0]) ? 1 : 0;
    }
    return v;
}

/* forward declaration */
int stat(const char *path, struct stat *st);

static void dbg(const char *fn, const char *from, const char *to)
{
    if (dbg_on()) {
        dprintf(2, "[nemu-test-env] %s: %s -> %s\n", fn, from, to);
    }
}

/*
 * Rewrite path:
 *   rule A: /tmp/...            → $NEMU_TMP_BASE/...
 *   rule B: /usr/bin/qemu-...   → $NEMU_QEMU_STUB_DIR/qemu-...
 * Hit: return thread-local static buffer; miss: return NULL.
 */
static const char *maybe_redirect(const char *path)
{
    static __thread char rbuf[4096];

    if (!path || path[0] != '/') {
        return NULL;
    }

    if (strncmp(path, "/tmp/", 5) == 0) {
        const char *base = env_once("NEMU_TMP_BASE");
        if (base && base[0]) {
            snprintf(rbuf, sizeof(rbuf), "%s/%s", base, path + 5);
            dbg("redirect", path, rbuf);
            return rbuf;
        }
        return NULL;
    }

    if (strncmp(path, "/usr/bin/qemu-", 14) == 0) {
        const char *stub = env_once("NEMU_QEMU_STUB_DIR");
        if (stub && stub[0]) {
            snprintf(rbuf, sizeof(rbuf), "%s/%s", stub, path + 9);
            dbg("redirect", path, rbuf);
            return rbuf;
        }
        return NULL;
    }

    return NULL;
}

/* --- getpwuid: return fake passwd --------------------------- */

static const char *fake_home(void)
{
    const char *h = getenv("NEMU_FAKE_HOME");
    return (h && h[0]) ? h : "/storage/Users/currentUser";
}

struct passwd *getpwuid(uid_t uid)
{
    static struct passwd pw;
    static char pw_name[64];
    static char pw_dir[4096];
    static int inited = 0;

    if (!inited) {
        snprintf(pw_name, sizeof(pw_name), "nemu-test");
        snprintf(pw_dir, sizeof(pw_dir), "%s", fake_home());
        memset(&pw, 0, sizeof(pw));
        pw.pw_name = pw_name;
        pw.pw_uid = uid;
        pw.pw_gid = uid;
        pw.pw_dir = pw_dir;
        pw.pw_shell = (char *)"/bin/sh";
        inited = 1;
    }
    pw.pw_uid = uid;
    if (dbg_on()) {
        dprintf(2, "[nemu-test-env] getpwuid(%u) -> home=%s\n",
                (unsigned)uid, pw_dir);
    }
    return &pw;
}

/* --- path-based syscall interception ------------------------------- */

int mkdir(const char *path, mode_t mode)
{
    static int (*real)(const char *, mode_t);
    if (!real) real = dlsym(RTLD_NEXT, "mkdir");
    const char *r = maybe_redirect(path);
    return real(r ? r : path, mode);
}

int mkdirat(int dirfd, const char *path, mode_t mode)
{
    static int (*real)(int, const char *, mode_t);
    if (!real) real = dlsym(RTLD_NEXT, "mkdirat");
    const char *r = maybe_redirect(path);
    return real(dirfd, r ? r : path, mode);
}

FILE *fopen(const char *path, const char *mode)
{
    static FILE *(*real)(const char *, const char *);
    if (!real) real = dlsym(RTLD_NEXT, "fopen");
    const char *r = maybe_redirect(path);
    return real(r ? r : path, mode);
}

/* muslCNfopen64/open64/stat64 CN */

int open(const char *path, int flags, ...)
{
    static int (*real)(const char *, int, ...);
    if (!real) real = dlsym(RTLD_NEXT, "open");
    const char *r = maybe_redirect(path);
    if (dbg_on()) {
        dbg("open", path ? path : "()", r ? r : (path ? path : "()"));
    }
    mode_t mode = 0;
    if (flags & (O_CREAT | O_TMPFILE)) {
        va_list ap;
        va_start(ap, flags);
        mode = va_arg(ap, mode_t);
        va_end(ap);
    }
    return real(r ? r : path, flags, mode);
}

/* openat: libarchive file IO uses openat(AT_FDCWD) on Linux */
int openat(int dirfd, const char *path, int flags, ...)
{
    static int (*real)(int, const char *, int, ...);
    if (!real) real = dlsym(RTLD_NEXT, "openat");
    const char *r = maybe_redirect(path);
    if (dbg_on()) {
        dbg("openat", path ? path : "()", r ? r : (path ? path : "()"));
    }
    mode_t mode = 0;
    if (flags & (O_CREAT | O_TMPFILE)) {
        va_list ap;
        va_start(ap, flags);
        mode = va_arg(ap, mode_t);
        va_end(ap);
    }
    return real(dirfd, r ? r : path, flags, mode);
}

int stat(const char *path, struct stat *st)
{
    static int (*real)(const char *, struct stat *);
    if (!real) real = dlsym(RTLD_NEXT, "stat");
    const char *r = maybe_redirect(path);
    return real(r ? r : path, st);
}

int __xstat(int ver, const char *path, struct stat *st)
{
    static int (*real)(int, const char *, struct stat *);
    if (!real) real = dlsym(RTLD_NEXT, "__xstat");
    const char *r = maybe_redirect(path);
    return real(ver, r ? r : path, st);
}

/* mkdtemp: nemu OVF import creates vm_dir/.tmp_ova/extract_XXXXXX.
 * Strategy: create the dir under $NEMU_TMP_BASE, then rewrite the 'X'
 * suffix of the original template with the real random suffix (the /tmp/...
 * prefix is kept so later path ops map to the same place via the same rule).
 */
char *mkdtemp(char *tmpl)
{
    static char *(*real)(char *);
    if (!real) real = dlsym(RTLD_NEXT, "mkdtemp");

    const char *r = maybe_redirect(tmpl);
    if (!r || r == tmpl) {
        return real(tmpl);
    }

    /* create the dir at the redirected path (independent buffer, no length worry) */
    char *redirected = strdup(r);
    if (!redirected) {
        errno = ENOMEM;
        return NULL;
    }
    if (!real(redirected)) {
        free(redirected);
        return NULL;  /* errno CN real_mkdtemp CN */
    }

    /* Extract the random suffix from the created dir name (basename after
     * the last '/'); replace the template 'X' run with the actual suffix. */
    const char *actual_base = strrchr(redirected, '/');
    actual_base = actual_base ? actual_base + 1 : redirected;
    char *tmpl_base = strrchr(tmpl, '/');
    tmpl_base = tmpl_base ? tmpl_base + 1 : tmpl;
    /* Template basename is like "extract_XXXXXX": keep the prefix before */
    /* the first 'X'. Find the start of the X run in the basename. */
    char *x_start = strchr(tmpl_base, 'X');
    if (x_start) {
        /* Use the actual suffix (part of actual_base after the common prefix). */
        size_t prefix_len = (size_t)(x_start - tmpl_base);
        if (strlen(actual_base) >= prefix_len) {
            snprintf(x_start, strlen(x_start) + 1, "%s",
                     actual_base + prefix_len);
        }
    }
    free(redirected);
    return tmpl;
}

/* chdir: nemu OVF extract temporarily chdirs into the extract dir (/tmp/...) */
int chdir(const char *path)
{
    static int (*real)(const char *);
    if (!real) real = dlsym(RTLD_NEXT, "chdir");
    const char *r = maybe_redirect(path);
    return real(r ? r : path);
}

/* getcwd: nm_ovf_extract saves cwd before chdir and the value is used
 * to chdir back later. If cwd itself is redirected (uncommon) no action
 * is needed; normally cwd is the original dir, pass through. */

/* statvfs: nm_hw_disk_free checks free space of vm_dir */
int statvfs(const char *path, struct statvfs *buf)
{
    static int (*real)(const char *, struct statvfs *);
    if (!real) real = dlsym(RTLD_NEXT, "statvfs");
    const char *r = maybe_redirect(path);
    return real(r ? r : path, buf);
}

int lstat(const char *path, struct stat *st)
{
    static int (*real)(const char *, struct stat *);
    if (!real) real = dlsym(RTLD_NEXT, "lstat");
    const char *r = maybe_redirect(path);
    return real(r ? r : path, st);
}

int access(const char *path, int mode)
{
    static int (*real)(const char *, int);
    if (!real) real = dlsym(RTLD_NEXT, "access");
    const char *r = maybe_redirect(path);
    return real(r ? r : path, mode);
}

int faccessat(int dirfd, const char *path, int mode, int flags)
{
    static int (*real)(int, const char *, int, int);
    if (!real) real = dlsym(RTLD_NEXT, "faccessat");
    const char *r = maybe_redirect(path);
    return real(dirfd, r ? r : path, mode, flags);
}

DIR *opendir(const char *path)
{
    static DIR *(*real)(const char *);
    if (!real) real = dlsym(RTLD_NEXT, "opendir");
    const char *r = maybe_redirect(path);
    return real(r ? r : path);
}

int unlink(const char *path)
{
    static int (*real)(const char *);
    if (!real) real = dlsym(RTLD_NEXT, "unlink");
    const char *r = maybe_redirect(path);
    return real(r ? r : path);
}

int rmdir(const char *path)
{
    static int (*real)(const char *);
    if (!real) real = dlsym(RTLD_NEXT, "rmdir");
    const char *r = maybe_redirect(path);
    return real(r ? r : path);
}

int remove(const char *path)
{
    static int (*real)(const char *);
    if (!real) real = dlsym(RTLD_NEXT, "remove");
    const char *r = maybe_redirect(path);
    return real(r ? r : path);
}

int rename(const char *old, const char *new)
{
    static int (*real)(const char *, const char *);
    if (!real) real = dlsym(RTLD_NEXT, "rename");
    /* maybe_redirect returns a thread-local static buffer; snapshot the
     * first result before resolving the second, otherwise both pointers
     * alias the same buffer and real rename gets (new, new). */
    const char *ro_raw = maybe_redirect(old);
    char ro_copy[4096];
    const char *ro = NULL;
    if (ro_raw) {
        snprintf(ro_copy, sizeof(ro_copy), "%s", ro_raw);
        ro = ro_copy;
    }
    const char *rn = maybe_redirect(new);
    return real(ro ? ro : old, rn ? rn : new);
}

int chmod(const char *path, mode_t mode)
{
    static int (*real)(const char *, mode_t);
    if (!real) real = dlsym(RTLD_NEXT, "chmod");
    const char *r = maybe_redirect(path);
    return real(r ? r : path, mode);
}

int truncate(const char *path, off_t len)
{
    static int (*real)(const char *, off_t);
    if (!real) real = dlsym(RTLD_NEXT, "truncate");
    const char *r = maybe_redirect(path);
    return real(r ? r : path, len);
}

char *realpath(const char *path, char *resolved)
{
    static char *(*real)(const char *, char *);
    if (!real) real = dlsym(RTLD_NEXT, "realpath");
    const char *r = maybe_redirect(path);
    return real(r ? r : path, resolved);
}

/* execvp/execv: nm_spawn_process launches the qemu stub via execvp */
int execvp(const char *file, char *const argv[])
{
    static int (*real)(const char *, char *const *);
    if (!real) real = dlsym(RTLD_NEXT, "execvp");
    const char *r = maybe_redirect(file);
    return real(r ? r : file, argv);
}

ssize_t readlink(const char *path, char *buf, size_t sz)
{
    static ssize_t (*real)(const char *, char *, size_t);
    if (!real) real = dlsym(RTLD_NEXT, "readlink");
    const char *r = maybe_redirect(path);
    return real(r ? r : path, buf, sz);
}
