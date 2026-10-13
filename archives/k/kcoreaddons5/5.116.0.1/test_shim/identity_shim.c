/*
 * identity_shim.c — getpwuid/getgrgid shim for the OHOS sandbox uid.
 *
 * The device ships /etc/passwd (392 entries) but has none for the uid this
 * session runs as (20020101) nor for its gid, so getpwuid()/getgrgid() return
 * NULL.  kcoreaddons5's kusertest asserts user.isValid() / group.isValid() /
 * non-empty names / a group that lists its users, which are exactly those
 * lookups: the *identity data* about the process's own uid is missing, not
 * libKF5CoreAddons.
 *
 * The shim answers the passwd/group calls about the process's own identity and
 * **passes everything else through to libc via dlsym(RTLD_NEXT, ...)** - the
 * device's real /etc/passwd and /etc/group stay authoritative for every other
 * uid, gid, name and enumeration (a first version answered NULL for the rest
 * and broke kshelltest, which resolves other identities).
 *
 * Technique precedent: the dbus recipe's libnopw.so shim
 * (archives/d/dbus/1.14.10.3/test_upstream.sh), which exists for the same
 * reason - the sandbox uid has no passwd entry there either.
 *
 * Build:  <clang> -shared -fPIC -o identity_shim.so identity_shim.c -ldl
 * Use:    LD_PRELOAD=<abs path>/identity_shim.so <test binary>
 */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <errno.h>
#include <grp.h>
#include <pwd.h>
#include <stdio.h>
#include <string.h>
#include <sys/types.h>
#include <unistd.h>

static const char kName[] = "ohos";
static const char kHome[] = "/storage/Users/currentUser";
static const char kShell[] = "/bin/sh";

static int is_self_uid(uid_t uid) { return uid == getuid(); }
static int is_self_gid(gid_t gid) { return gid == getgid(); }
static int is_self_name(const char *name)
{
    return name && strcmp(name, kName) == 0;
}

/* ---- constructor so a failure to build the shim is loud ----------------- */
__attribute__((constructor)) static void shim_loaded(void)
{
    if (!dlsym(RTLD_NEXT, "getpwuid")) {
        fprintf(stderr, "identity_shim: dlsym(RTLD_NEXT) unavailable\n");
    }
}

#define REAL(name) dlsym(RTLD_NEXT, name)

/* ---- passwd -------------------------------------------------------------- */

struct passwd *getpwuid(uid_t uid)
{
    static struct passwd pw;
    if (!is_self_uid(uid)) {
        return ((struct passwd *(*)(uid_t))REAL("getpwuid"))(uid);
    }
    pw.pw_name = (char *)kName;
    pw.pw_passwd = (char *)"";
    pw.pw_uid = uid;
    pw.pw_gid = getgid();
    pw.pw_gecos = (char *)kName;
    pw.pw_dir = (char *)kHome;
    pw.pw_shell = (char *)kShell;
    return &pw;
}

int getpwuid_r(uid_t uid, struct passwd *result, char *buf, size_t buflen,
               struct passwd **res)
{
    if (!is_self_uid(uid)) {
        return ((int (*)(uid_t, struct passwd *, char *, size_t,
                         struct passwd **))REAL("getpwuid_r"))(uid, result, buf,
                                                              buflen, res);
    }
    const size_t need = sizeof(kName) + sizeof(kHome) + sizeof(kShell);
    if (buflen < need) {
        *res = NULL;
        return ERANGE;
    }
    char *p = buf;
    result->pw_name = p; memcpy(p, kName, sizeof(kName)); p += sizeof(kName);
    result->pw_passwd = (char *)"";
    result->pw_uid = uid;
    result->pw_gid = getgid();
    result->pw_gecos = result->pw_name;
    result->pw_dir = p; memcpy(p, kHome, sizeof(kHome)); p += sizeof(kHome);
    result->pw_shell = p; memcpy(p, kShell, sizeof(kShell));
    *res = result;
    return 0;
}

struct passwd *getpwnam(const char *name)
{
    if (!is_self_name(name)) {
        return ((struct passwd *(*)(const char *))REAL("getpwnam"))(name);
    }
    return getpwuid(getuid());
}

int getpwnam_r(const char *name, struct passwd *result, char *buf,
               size_t buflen, struct passwd **res)
{
    if (!is_self_name(name)) {
        return ((int (*)(const char *, struct passwd *, char *, size_t,
                         struct passwd **))REAL("getpwnam_r"))(name, result, buf,
                                                              buflen, res);
    }
    return getpwuid_r(getuid(), result, buf, buflen, res);
}

/* Let the passwd enumeration find the synthetic entry as well: KUserGroup
 * collects a group's users by walking the passwd database. */
static int g_pwent_served;

void setpwent(void)
{
    g_pwent_served = 0;
    ((void (*)(void))REAL("setpwent"))();
}

void endpwent(void)
{
    g_pwent_served = 0;
    ((void (*)(void))REAL("endpwent"))();
}

struct passwd *getpwent(void)
{
    struct passwd *entry = ((struct passwd *(*)(void))REAL("getpwent"))();
    if (entry) {
        return entry;
    }
    if (!g_pwent_served) {
        g_pwent_served = 1;
        return getpwuid(getuid());
    }
    return NULL;
}

/* ---- group --------------------------------------------------------------- */

static char *g_self_members[] = { (char *)kName, NULL };

struct group *getgrgid(gid_t gid)
{
    static struct group gr;
    if (!is_self_gid(gid)) {
        return ((struct group *(*)(gid_t))REAL("getgrgid"))(gid);
    }
    gr.gr_name = (char *)kName;
    gr.gr_passwd = (char *)"";
    gr.gr_gid = gid;
    gr.gr_mem = g_self_members; /* the group lists its single member */
    return &gr;
}

int getgrgid_r(gid_t gid, struct group *result, char *buf, size_t buflen,
               struct group **res)
{
    if (!is_self_gid(gid)) {
        return ((int (*)(gid_t, struct group *, char *, size_t,
                         struct group **))REAL("getgrgid_r"))(gid, result, buf,
                                                              buflen, res);
    }
    if (buflen < sizeof(kName)) {
        *res = NULL;
        return ERANGE;
    }
    memcpy(buf, kName, sizeof(kName));
    result->gr_name = buf;
    result->gr_passwd = (char *)"";
    result->gr_gid = gid;
    result->gr_mem = g_self_members;
    *res = result;
    return 0;
}

struct group *getgrnam(const char *name)
{
    if (!is_self_name(name)) {
        return ((struct group *(*)(const char *))REAL("getgrnam"))(name);
    }
    return getgrgid(getgid());
}

int getgrnam_r(const char *name, struct group *result, char *buf, size_t buflen,
               struct group **res)
{
    if (!is_self_name(name)) {
        return ((int (*)(const char *, struct group *, char *, size_t,
                         struct group **))REAL("getgrnam_r"))(name, result, buf,
                                                              buflen, res);
    }
    return getgrgid_r(getgid(), result, buf, buflen, res);
}

static int g_grent_served;

void setgrent(void)
{
    g_grent_served = 0;
    ((void (*)(void))REAL("setgrent"))();
}

void endgrent(void)
{
    g_grent_served = 0;
    ((void (*)(void))REAL("endgrent"))();
}

struct group *getgrent(void)
{
    struct group *entry = ((struct group *(*)(void))REAL("getgrent"))();
    if (entry) {
        return entry;
    }
    if (!g_grent_served) {
        g_grent_served = 1;
        return getgrgid(getgid());
    }
    return NULL;
}

/* Linux/musl: getgrouplist may not exist in every libc; guard the fallback. */
int getgrouplist(const char *user, gid_t gid, gid_t *groups, int *ngroups)
{
    int (*real)(const char *, gid_t, gid_t *, int *) = REAL("getgrouplist");
    if (!is_self_name(user) && real) {
        return real(user, gid, groups, ngroups);
    }
    if (*ngroups < 1) {
        *ngroups = 1;
        return -1;
    }
    groups[0] = gid;
    *ngroups = 1;
    return 1;
}
