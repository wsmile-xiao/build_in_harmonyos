/*
 * ohos_tmpdir_shim.c — LD_PRELOAD shim for pycairo's upstream pytest on
 * HarmonyOS PC.
 *
 * HarmonyOS mounts /tmp read-only (erofs, see knowledge/doc/E002.md). cairo's
 * PS surface unconditionally creates a temporary file at surface creation time
 * (_cairo_ps_surface_create_internal -> _cairo_tmpfile(), cairo-misc.c): it
 * opens P_tmpdir ("/tmp") with O_TMPFILE and falls back to tmpfile(); it never
 * consults $TMPDIR. Every cairo.PSSurface(...) therefore fails with
 * CAIRO_STATUS_TEMP_FILE_ERROR ("error creating or writing to a temporary
 * file") even though HMBS injects a writable $TMPDIR.
 *
 * This shim interposes open() (O_TMPFILE calls only) and tmpfile() and
 * redirects the temp file into the first writable directory among
 * $TMPDIR, $TMP, $TEMP and $HOME/tmp. The file is created with O_CREAT|O_EXCL
 * and unlinked immediately, preserving the unnamed O_TMPFILE / tmpfile()
 * semantics. All other calls pass through untouched.  (open64 needs no
 * separate interposition: on OHOS musl it is a macro aliasing open.)
 *
 * Build with the OHOS clang toolchain (-fPIC -shared), sign with
 * /data/service/hnp/bin/binary-sign-tool, and set LD_PRELOAD for the pytest
 * process (see conanfile.py _build_tmpdir_shim / _run_upstream_tests).
 */

#define _GNU_SOURCE 1

#include <dlfcn.h>
#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

/* ---------------------------------------------------------------- helpers */

static int (*real_open_fn) (const char *, int, ...) = NULL;
static FILE *(*real_tmpfile_fn) (void) = NULL;

static void
resolve_real (void)
{
    if (real_open_fn == NULL)
        real_open_fn = (int (*)(const char *, int, ...)) dlsym (RTLD_NEXT, "open");
    if (real_tmpfile_fn == NULL)
        real_tmpfile_fn = (FILE *(*)(void)) dlsym (RTLD_NEXT, "tmpfile");
}

/* Lazily pick the first writable directory. Returns NULL if none usable. */
static const char *
writable_tmpdir (void)
{
    static char g_tmp[PATH_MAX];
    static int g_state = 0; /* 0=unknown, 1=ok, -1=none */
    char probe[PATH_MAX];
    const char *cands[4];
    char home_tmp[PATH_MAX];
    const char *home;
    int i, fd, n;

    if (g_state == 1)
        return g_tmp;
    if (g_state == -1)
        return NULL;

    cands[0] = getenv ("TMPDIR");
    cands[1] = getenv ("TMP");
    cands[2] = getenv ("TEMP");
    home = getenv ("HOME");
    home_tmp[0] = '\0';
    if (home != NULL && home[0] != '\0') {
        n = snprintf (home_tmp, sizeof home_tmp, "%s/tmp", home);
        if (n > 0 && n < (int) sizeof home_tmp)
            cands[3] = home_tmp;
        else
            cands[3] = NULL;
    } else {
        cands[3] = NULL;
    }

    for (i = 0; i < 4; i++) {
        const char *d = cands[i];
        if (d == NULL || d[0] == '\0')
            continue;
        n = snprintf (probe, sizeof probe, "%s/.tmpdir-probe-%ld", d, (long) getpid ());
        if (n <= 0 || n >= (int) sizeof probe)
            continue;
        resolve_real ();
        if (real_open_fn == NULL)
            continue;
        fd = real_open_fn (probe, O_CREAT | O_EXCL | O_WRONLY, 0600);
        if (fd < 0)
            continue; /* not writable, try next candidate */
        close (fd);
        unlink (probe);
        if (snprintf (g_tmp, sizeof g_tmp, "%s", d) > 0) {
            g_state = 1;
            return g_tmp;
        }
    }
    g_state = -1;
    return NULL;
}

/* ------------------------------------------------------------- interposed */

static int
interpose_open (const char *path, int flags, mode_t mode)
{
    resolve_real ();
    if (real_open_fn == NULL)
        return -1; /* libc always present; cannot happen */

#ifdef O_TMPFILE
    if (flags & O_TMPFILE) {
        const char *d = writable_tmpdir ();
        if (d != NULL) {
            char buf[PATH_MAX];
            int i;
            for (i = 0; i < 128; i++) {
                int n = snprintf (buf, sizeof buf, "%s/.cairo-tmp-%ld-%d",
                                  d, (long) getpid (), i);
                if (n <= 0 || n >= (int) sizeof buf)
                    break;
                {
                    int fd = real_open_fn (buf,
                                           (flags & ~(O_TMPFILE | O_DIRECTORY)) | O_CREAT | O_EXCL,
                                           0600);
                    if (fd >= 0) {
                        unlink (buf); /* unnamed, like O_TMPFILE / tmpfile() */
                        return fd;
                    }
                    if (errno != EEXIST)
                        break;
                }
            }
            /* fall through to the real open on the original path */
        }
    }
#endif /* O_TMPFILE */
    return real_open_fn (path, flags, mode);
}

int
open (const char *path, int flags, ...)
{
    mode_t mode = 0;
    if (flags & O_CREAT) {
        va_list ap;
        va_start (ap, flags);
        mode = (mode_t) va_arg (ap, int);
        va_end (ap);
    }
    return interpose_open (path, flags, mode);
}

/* NOTE: no open64() interposition here — on OHOS (musl) fcntl.h defines
 * `open64` as a macro aliasing `open` (#define open64 open), so defining a
 * separate open64() function would expand to a redefinition of open() and
 * fail to compile.  Interposing open() alone covers all callers, including
 * those that use the open64 name.
 */

FILE *
tmpfile (void)
{
    resolve_real ();
    if (real_tmpfile_fn == NULL)
        return NULL;

    {
        const char *d = writable_tmpdir ();
        if (d != NULL) {
            char buf[PATH_MAX];
            int i;
            for (i = 0; i < 128; i++) {
                int n = snprintf (buf, sizeof buf, "%s/.tmpfile-%ld-%d",
                                  d, (long) getpid (), i);
                if (n <= 0 || n >= (int) sizeof buf)
                    break;
                {
                    int fd = real_open_fn (buf, O_CREAT | O_EXCL | O_RDWR, 0600);
                    if (fd >= 0) {
                        FILE *f;
                        unlink (buf);
                        f = fdopen (fd, "w+b");
                        if (f != NULL)
                            return f;
                        close (fd);
                        break;
                    }
                    if (errno != EEXIST)
                        break;
                }
            }
        }
    }
    return real_tmpfile_fn ();
}
