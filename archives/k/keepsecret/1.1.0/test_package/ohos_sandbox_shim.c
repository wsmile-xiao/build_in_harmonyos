/*
 * OHOS sandbox test shim for keepsecret 1.1.0 (build_in_harmonyos).
 *
 * Preloaded (LD_PRELOAD) only inside the test_package launch smoke; it is not
 * part of the packaged application.
 *
 * Why it is needed - two independent gaps in this build sandbox:
 *
 * 1. The sandbox user has no /etc/passwd entry (getpwuid(uid) raises
 *    KeyError), so dbus-daemon's peer-UID lookup for the session bus fails and
 *    every client connection is rejected. Unknown UIDs are served a synthetic
 *    passwd/group entry here; resolvable ones fall through to the real libc
 *    lookup via RTLD_NEXT. keepsecret constructs
 *    KDBusService(KDBusService::Unique) before the QML engine exists, so
 *    without a connectable bus the process exits before Main.qml loads and the
 *    launch smoke could not observe what it claims to.
 *    (kio-kwallet 6.28.0 precedent.)
 *
 * 2. Two libraries in the graph ship a libintl.so.8 with different export
 *    sets: glib's proxy-libintl build exports g_libintl_*, gettext's exports
 *    libintl_*. libglib-2.0.so calls g_libintl_*, libKF6I18n.so calls
 *    libintl_*. Depending on which one the loader picks, the other set is
 *    unresolved. Forwarding both name families here (dlopen'ing whichever
 *    libintl resolves) makes the smoke run regardless of load order.
 */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <grp.h>
#include <pwd.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/types.h>
#include <unistd.h>

/* ---- passwd/group: synthetic entries for unresolvable UIDs/GIDs ------- */

static struct passwd *fill_pw(uid_t uid)
{
    static struct passwd p;
    static char name[64], dir[128], shell[32], gecos[8], pass[8];
    snprintf(name, sizeof(name), "u%u", (unsigned)uid);
    const char *home = getenv("HOME");
    if (!home) home = "/tmp";
    snprintf(dir, sizeof(dir), "%s", home);
    strcpy(shell, "/bin/sh");
    strcpy(gecos, "x");
    strcpy(pass, "x");
    p.pw_name = name;
    p.pw_passwd = pass;
    p.pw_uid = uid;
    p.pw_gid = 1000;
    p.pw_gecos = gecos;
    p.pw_dir = dir;
    p.pw_shell = shell;
    return &p;
}

typedef struct passwd *(*real_pwuid_t)(uid_t);
typedef int (*real_pwuid_r_t)(uid_t, struct passwd *, char *, size_t, struct passwd **);
typedef struct passwd *(*real_pwnam_t)(const char *);
typedef int (*real_pwnam_r_t)(const char *, struct passwd *, char *, size_t, struct passwd **);

struct passwd *getpwuid(uid_t uid)
{
    real_pwuid_t real = (real_pwuid_t)dlsym(RTLD_NEXT, "getpwuid");
    if (real) {
        struct passwd *r = real(uid);
        if (r) return r;
    }
    return fill_pw(uid);
}

int getpwuid_r(uid_t uid, struct passwd *pw, char *buf, size_t len, struct passwd **out)
{
    real_pwuid_r_t real = (real_pwuid_r_t)dlsym(RTLD_NEXT, "getpwuid_r");
    if (real) {
        if (real(uid, pw, buf, len, out) == 0) return 0;
    }
    struct passwd *p = fill_pw(uid);
    *pw = *p;
    if (out) *out = pw;
    return 0;
}

struct passwd *getpwnam(const char *n)
{
    real_pwnam_t real = (real_pwnam_t)dlsym(RTLD_NEXT, "getpwnam");
    if (real) {
        struct passwd *r = real(n);
        if (r) return r;
    }
    return fill_pw(geteuid());
}

int getpwnam_r(const char *n, struct passwd *pw, char *buf, size_t len, struct passwd **out)
{
    real_pwnam_r_t real = (real_pwnam_r_t)dlsym(RTLD_NEXT, "getpwnam_r");
    if (real) {
        if (real(n, pw, buf, len, out) == 0) return 0;
    }
    struct passwd *p = fill_pw(geteuid());
    *pw = *p;
    if (out) *out = pw;
    return 0;
}

static struct group *fill_gr(gid_t gid)
{
    static struct group g;
    static char name[64];
    static char *mem[1];
    snprintf(name, sizeof(name), "g%u", (unsigned)gid);
    g.gr_name = name;
    g.gr_passwd = "x";
    g.gr_gid = gid;
    g.gr_mem = mem;
    mem[0] = NULL;
    return &g;
}

struct group *getgrgid(gid_t gid) { return fill_gr(gid); }
struct group *getgrnam(const char *n) { (void)n; return fill_gr(getegid()); }

/* ---- libintl: forward both g_libintl_* and libintl_* ------------------- */

static void *intl_handle;

static void *intl_sym(const char *plain, const char *prefixed)
{
    void *s = NULL;
    if (intl_handle) {
        s = dlsym(intl_handle, prefixed);
        if (!s) s = dlsym(intl_handle, plain);
    }
    return s;
}

__attribute__((constructor))
static void shim_init(void)
{
    intl_handle = dlopen("libintl.so.8", RTLD_NOW | RTLD_GLOBAL);
    if (!intl_handle) intl_handle = dlopen("libintl.so", RTLD_NOW | RTLD_GLOBAL);
}

char *g_libintl_gettext(const char *m)
{
    void *f = intl_sym("gettext", "libintl_gettext");
    return f ? ((char *(*)(const char *))f)(m) : (char *)m;
}
char *g_libintl_dgettext(const char *d, const char *m)
{
    void *f = intl_sym("dgettext", "libintl_dgettext");
    return f ? ((char *(*)(const char *, const char *))f)(d, m) : (char *)m;
}
char *g_libintl_dcgettext(const char *d, const char *m, int c)
{
    void *f = intl_sym("dcgettext", "libintl_dcgettext");
    return f ? ((char *(*)(const char *, const char *, int))f)(d, m, c) : (char *)m;
}
char *g_libintl_bindtextdomain(const char *d, const char *dir)
{
    void *f = intl_sym("bindtextdomain", "libintl_bindtextdomain");
    return f ? ((char *(*)(const char *, const char *))f)(d, dir) : (char *)d;
}
char *g_libintl_bind_textdomain_codeset(const char *d, const char *c)
{
    void *f = intl_sym("bind_textdomain_codeset", "libintl_bind_textdomain_codeset");
    return f ? ((char *(*)(const char *, const char *))f)(d, c) : (char *)d;
}
char *g_libintl_textdomain(const char *d)
{
    void *f = intl_sym("textdomain", "libintl_textdomain");
    return f ? ((char *(*)(const char *))f)(d) : (char *)d;
}
char *g_libintl_ngettext(const char *s1, const char *s2, unsigned long n)
{
    void *f = intl_sym("ngettext", "libintl_ngettext");
    return f ? ((char *(*)(const char *, const char *, unsigned long))f)(s1, s2, n)
             : (char *)(n == 1 ? s1 : s2);
}
char *g_libintl_dngettext(const char *d, const char *s1, const char *s2, unsigned long n)
{
    void *f = intl_sym("dngettext", "libintl_dngettext");
    return f ? ((char *(*)(const char *, const char *, const char *, unsigned long))f)(d, s1, s2, n)
             : (char *)(n == 1 ? s1 : s2);
}
char *g_libintl_dcngettext(const char *d, const char *s1, const char *s2, unsigned long n, int c)
{
    void *f = intl_sym("dcngettext", "libintl_dcngettext");
    return f ? ((char *(*)(const char *, const char *, const char *, unsigned long, int))f)(d, s1, s2, n, c)
             : (char *)(n == 1 ? s1 : s2);
}
void _proxy_libintl_deinit(void) {}

char *libintl_gettext(const char *m) { return g_libintl_gettext(m); }
char *libintl_dgettext(const char *d, const char *m) { return g_libintl_dgettext(d, m); }
char *libintl_dcgettext(const char *d, const char *m, int c) { return g_libintl_dcgettext(d, m, c); }
char *libintl_bindtextdomain(const char *d, const char *dir) { return g_libintl_bindtextdomain(d, dir); }
char *libintl_bind_textdomain_codeset(const char *d, const char *c) { return g_libintl_bind_textdomain_codeset(d, c); }
char *libintl_textdomain(const char *d) { return g_libintl_textdomain(d); }
char *libintl_ngettext(const char *s1, const char *s2, unsigned long n) { return g_libintl_ngettext(s1, s2, n); }
char *libintl_dngettext(const char *d, const char *s1, const char *s2, unsigned long n)
{
    return g_libintl_dngettext(d, s1, s2, n);
}
char *libintl_dcngettext(const char *d, const char *s1, const char *s2, unsigned long n, int c)
{
    return g_libintl_dcngettext(d, s1, s2, n, c);
}
