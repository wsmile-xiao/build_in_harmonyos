/*
 * yatest_tmpredir.c — test-only LD_PRELOAD shim for OHOS devices where /tmp
 * is a read-only filesystem (EROFS).
 *
 * Intercepts the common libc path APIs and transparently rewrites any path
 * under "/tmp/" (or exactly "/tmp") to $YADIFA_TEST_TMPDIR + suffix when that
 * variable is set. Everything else passes through untouched, so the packaged
 * binaries are not affected: the shim is only injected around the ctest phase
 * via LD_PRELOAD from the conan recipe build().
 *
 * Build: clang -shared -fPIC -O1 -o yatest_tmpredir.so yatest_tmpredir.c -ldl
 */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <fcntl.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/stat.h>
#include <sys/types.h>

static const char *redirect_root(void)
{
    const char *dir = getenv("YADIFA_TEST_TMPDIR");
    if (dir && dir[0]) {
        return dir;
    }
    return NULL; /* disabled */
}

/* Returns a malloc'd rewritten path if redirection applies, else NULL. */
static char *rewrite(const char *path)
{
    const char *root = redirect_root();
    if (!root || !path) {
        return NULL;
    }
    size_t rlen = strlen(root);
    /* POSIX collapses a leading run of slashes to one separator, and some
     * upstream test paths are built with a doubled one ("//tmp/x"), so match
     * on the component after the leading slashes instead of a literal prefix. */
    if (*path != 0x2f) {
        return NULL; /* not absolute */
    }
    const char *p = path + strspn(path, "/");
    if (strncmp(p, "tmp/", 4) == 0) {
        size_t len = rlen + strlen(p + 3) + 1;
        char *out = malloc(len);
        if (out) {
            snprintf(out, len, "%s%s", root, p + 3);
        }
        return out;
    }
    if (strcmp(p, "tmp") == 0) {
        return strdup(root);
    }
    return NULL;
}

/* The varargs entry points (open/openat) are written out explicitly below;
 * a generic macro would be harder to audit than the straight-line code. */

int open(const char *path, int flags, ...)
{
    static int (*real_open)(const char *, int, ...) = NULL;
    if (!real_open) {
        real_open = dlsym(RTLD_NEXT, "open");
    }
    mode_t mode = 0;
    if (flags & (O_CREAT | O_TMPFILE)) {
        va_list ap;
        va_start(ap, flags);
        mode = va_arg(ap, mode_t);
        va_end(ap);
        char *alt = rewrite(path);
        if (alt) {
            int rc = real_open(alt, flags, mode);
            free(alt);
            return rc;
        }
        return real_open(path, flags, mode);
    }
    char *alt = rewrite(path);
    if (alt) {
        int rc = real_open(alt, flags, mode);
        free(alt);
        return rc;
    }
    return real_open(path, flags);
}

/* open64/fopen64 are #define'd to open/fopen on musl, so they resolve to the
 * interposed open/fopen above and need no separate definitions. */

int openat(int dirfd, const char *path, int flags, ...)
{
    static int (*real_openat)(int, const char *, int, ...) = NULL;
    if (!real_openat) {
        real_openat = dlsym(RTLD_NEXT, "openat");
    }
    /* Only absolute /tmp paths are redirected; relative paths pass through. */
    if (path && path[0] == '/') {
        mode_t mode = 0;
        if (flags & (O_CREAT | O_TMPFILE)) {
            va_list ap;
            va_start(ap, flags);
            mode = va_arg(ap, mode_t);
            va_end(ap);
        }
        char *alt = rewrite(path);
        if (alt) {
            int rc = (flags & (O_CREAT | O_TMPFILE)) ? real_openat(dirfd, alt, flags, mode)
                                                     : real_openat(dirfd, alt, flags);
            free(alt);
            return rc;
        }
    }
    if (flags & (O_CREAT | O_TMPFILE)) {
        va_list ap;
        va_start(ap, flags);
        mode_t mode = va_arg(ap, mode_t);
        va_end(ap);
        return real_openat(dirfd, path, flags, mode);
    }
    return real_openat(dirfd, path, flags);
}

FILE *fopen(const char *path, const char *mode)
{
    static FILE *(*real_fopen)(const char *, const char *) = NULL;
    if (!real_fopen) {
        real_fopen = dlsym(RTLD_NEXT, "fopen");
    }
    char *alt = rewrite(path);
    FILE *rc = real_fopen(alt ? alt : path, mode);
    if (alt) {
        free(alt);
    }
    return rc;
}

int mkstemp(char *tmpl)
{
    static int (*real_mkstemp)(char *) = NULL;
    if (!real_mkstemp) {
        real_mkstemp = dlsym(RTLD_NEXT, "mkstemp");
    }
    char *alt = rewrite(tmpl);
    int rc;
    if (alt) {
        rc = real_mkstemp(alt);
        if (rc >= 0) {
            snprintf(tmpl, strlen(alt) + 1, "%s", alt);
        }
        free(alt);
    } else {
        rc = real_mkstemp(tmpl);
    }
    return rc;
}

int unlink(const char *path)
{
    static int (*real_unlink)(const char *) = NULL;
    if (!real_unlink) {
        real_unlink = dlsym(RTLD_NEXT, "unlink");
    }
    char *alt = rewrite(path);
    int rc = real_unlink(alt ? alt : path);
    if (alt) {
        free(alt);
    }
    return rc;
}

int rename(const char *oldp, const char *newp)
{
    static int (*real_rename)(const char *, const char *) = NULL;
    if (!real_rename) {
        real_rename = dlsym(RTLD_NEXT, "rename");
    }
    char *aold = rewrite(oldp);
    char *anew = rewrite(newp);
    int rc = real_rename(aold ? aold : oldp, anew ? anew : newp);
    if (aold) free(aold);
    if (anew) free(anew);
    return rc;
}

int mkdir(const char *path, mode_t mode)
{
    static int (*real_mkdir)(const char *, mode_t) = NULL;
    if (!real_mkdir) {
        real_mkdir = dlsym(RTLD_NEXT, "mkdir");
    }
    char *alt = rewrite(path);
    int rc = real_mkdir(alt ? alt : path, mode);
    if (alt) {
        free(alt);
    }
    return rc;
}

int stat(const char *path, struct stat *st)
{
    static int (*real_stat)(const char *, struct stat *) = NULL;
    if (!real_stat) {
        real_stat = dlsym(RTLD_NEXT, "stat");
    }
    char *alt = rewrite(path);
    int rc = real_stat(alt ? alt : path, st);
    if (alt) {
        free(alt);
    }
    return rc;
}

int access(const char *path, int mode)
{
    static int (*real_access)(const char *, int) = NULL;
    if (!real_access) {
        real_access = dlsym(RTLD_NEXT, "access");
    }
    char *alt = rewrite(path);
    int rc = real_access(alt ? alt : path, mode);
    if (alt) {
        free(alt);
    }
    return rc;
}

/* stdio helpers some tests use for temp artifacts */
int remove(const char *path)
{
    static int (*real_remove)(const char *) = NULL;
    if (!real_remove) {
        real_remove = dlsym(RTLD_NEXT, "remove");
    }
    char *alt = rewrite(path);
    int rc = real_remove(alt ? alt : path);
    if (alt) {
        free(alt);
    }
    return rc;
}

int creat(const char *path, mode_t mode)
{
    return open(path, O_CREAT | O_WRONLY | O_TRUNC, mode);
}
